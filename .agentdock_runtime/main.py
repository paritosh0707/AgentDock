"""
Generated dockrion Runtime
Agent: invoice-copilot
Framework: langgraph

This runtime leverages the full dockrion infrastructure:
- Adapter layer for framework-agnostic agent invocation
- Schema validation for inputs/outputs
- Common utilities for error handling and logging
"""
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Add project root to Python path so agent modules can be imported
# Runtime is in .dockrion_runtime/, project root is parent directory
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import dockrion packages
from dockrion_adapters import get_adapter
from dockrion_schema import DockSpec
from dockrion_common.errors import DockrionError, ValidationError
from dockrion_common.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="invoice-copilot",
    description="Extracts fields from invoices and returns a normalized JSON summary.",
    version="1.0.0"
)

# Load agent specification
SPEC_DATA = {'version': '1.0', 'agent': {'name': 'invoice-copilot', 'description': 'Extracts fields from invoices and returns a normalized JSON summary.', 'entrypoint': 'examples.invoice_copilot.app.graph:build_graph', 'framework': 'langgraph'}, 'model': {'provider': 'openai', 'name': 'gpt-4o-mini', 'temperature': 0.2, 'max_tokens': 1500, 'endpoint': None, 'extra': {'response_format': 'json_object'}}, 'io_schema': {'input': {'type': 'object', 'properties': {'document_text': {'type': 'string'}, 'currency_hint': {'type': 'string', 'enum': ['INR', 'USD', 'EUR']}, 'vendor_hint': {'type': 'string'}}, 'required': ['document_text'], 'items': None, 'description': None}, 'output': {'type': 'object', 'properties': {'vendor': {'type': 'string'}, 'invoice_number': {'type': 'string'}, 'invoice_date': {'type': 'string'}, 'total_amount': {'type': 'number'}, 'currency': {'type': 'string'}, 'line_items': {'type': 'array', 'items': {'type': 'object', 'required': ['description', 'qty', 'unit_price', 'amount'], 'properties': {'description': {'type': 'string'}, 'qty': {'type': 'number'}, 'unit_price': {'type': 'number'}, 'amount': {'type': 'number'}}}}, 'notes': {'type': 'string'}}, 'required': ['vendor', 'invoice_number', 'invoice_date', 'line_items', 'total_amount'], 'items': None, 'description': None}}, 'arguments': {'timeout_sec': 20, 'enable_streaming': True}, 'policies': None, 'auth': {'mode': 'api_key', 'api_keys': {'enabled': True, 'rotation_days': 30}, 'roles': [{'name': 'admin', 'permissions': ['deploy', 'rollback', 'invoke', 'view_metrics', 'key_manage', 'read_logs', 'read_docs']}, {'name': 'developer', 'permissions': ['invoke', 'view_metrics', 'read_logs']}, {'name': 'viewer', 'permissions': ['invoke']}], 'rate_limits': {'admin': '1000/m', 'developer': '300/m', 'viewer': '60/m'}}, 'observability': None, 'expose': {'rest': True, 'streaming': 'sse', 'port': 8080, 'host': '0.0.0.0', 'cors': {'origins': ['http://localhost:3000', 'http://localhost:5173'], 'methods': ['GET', 'POST', 'OPTIONS']}}, 'metadata': {'maintainer': 'Paritosh <paritosh@example.com>', 'version': 'v1.0.0', 'tags': ['finance', 'extraction', 'demo']}}
SPEC = DockSpec.model_validate(SPEC_DATA)

# Initialize adapter and load agent
logger.info(f"Initializing {SPEC.agent.framework} adapter...")
adapter = get_adapter(SPEC.agent.framework)

logger.info(f"Loading agent from {SPEC.agent.entrypoint}...")
adapter.load(SPEC.agent.entrypoint)

logger.info(f"Agent {SPEC.agent.name} loaded successfully")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "agent": SPEC.agent.name}


@app.get("/schema")
async def get_schema():
    """Get input/output schema"""
    return getattr(SPEC, "io_schema", {})



@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post("/invoke")
async def invoke(request: Request):
    """Invoke the agent with input payload.
    
    Uses the adapter layer for framework-agnostic invocation.
    """
    try:
        # Get payload
        payload = await request.json()
        
        logger.info(f"Received invocation request: {{payload}}")
        
        # Optional: Check API key
        api_key = request.headers.get("X-API-Key")
        if os.environ.get("DOCKRION_REQUIRE_AUTH", "false").lower() == "true":
            if not api_key or api_key != os.environ.get("DOCKRION_API_KEY", ""):
                logger.warning("Unauthorized access attempt")
                raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        # Optional: Validate input against schema
        if SPEC.io_schema and SPEC.io_schema.input:
            # TODO: Add input validation in V1.1+
            pass
        
        # Invoke agent using adapter layer
        logger.info("Invoking agent via adapter...")
        start_time = time.time()
        result = adapter.invoke(payload)
        latency = time.time() - start_time
        
        logger.info(f"Agent invocation completed in {{latency:.3f}}s")
        
        # Optional: Validate output against schema
        if SPEC.io_schema and SPEC.io_schema.output:
            # TODO: Add output validation in V1.1+
            pass
        
        # Return response
        return JSONResponse({
            "success": True,
            "output": result,
            "latency_s": round(latency, 3),
            "agent": SPEC.agent.name,
            "framework": SPEC.agent.framework
        })
        
    except ValidationError as e:
        logger.error(f"Validation error: {{e}}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e),
                "error_type": "ValidationError"
            }
        )
    except DockrionError as e:
        logger.error(f"dockrion error: {{e}}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": "DockrionError"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {{e}}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
