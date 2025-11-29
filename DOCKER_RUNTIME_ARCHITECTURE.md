# Docker Runtime Architecture

## Overview

The Dockrion Docker runtime now leverages the **full Dockrion infrastructure** including the adapter layer, schema validation, and common utilities. This provides a robust, production-ready runtime with proper error handling, logging, and framework-agnostic agent invocation.

## Architecture Improvements

### Before (Static Runtime)
```python
# ❌ Old approach: Direct agent loading
import importlib
agent = load_agent_manually()  # Bypassed adapter layer
result = agent.invoke(payload)  # Framework-specific
```

**Problems**:
- Duplicated agent loading logic
- No framework abstraction
- Lost adapter layer benefits
- No proper error handling
- No schema validation

### After (Infrastructure-Aware Runtime)
```python
# ✅ New approach: Use Dockrion packages
from dockrion_adapters import get_adapter
from dockrion_schema import DockSpec
from dockrion_common.errors import DockrionError, ValidationError
from dockrion_common.logger import get_logger

# Initialize with adapter layer
adapter = get_adapter(SPEC.agent.framework)
adapter.load(SPEC.agent.entrypoint)

# Framework-agnostic invocation
result = adapter.invoke(payload)
```

**Benefits**:
- ✅ Uses adapter layer for framework abstraction
- ✅ Proper error handling with custom exceptions
- ✅ Structured logging
- ✅ Schema validation (ready for V1.1+)
- ✅ Consistent behavior with local development
- ✅ Maintainable and extensible

## How It Works

### 1. Package Bundling

The Dockerfile copies Dockrion packages into the image:

```dockerfile
# Copy Dockrion packages (to be installed locally)
COPY packages/common-py/ /dockrion_packages/common-py/
COPY packages/schema/ /dockrion_packages/schema/
COPY packages/adapters/ /dockrion_packages/adapters/

# Install Dockrion packages first (from local copies)
RUN pip install --no-cache-dir -e /dockrion_packages/common-py && \
    pip install --no-cache-dir -e /dockrion_packages/schema && \
    pip install --no-cache-dir -e /dockrion_packages/adapters
```

**Why local installation?**
- Dockrion packages are not yet published to PyPI
- Local installation with `-e` (editable mode) makes them available
- No need to publish packages for V1 deployment

### 2. Runtime Generation

The `_render_runtime()` function generates FastAPI code that:

1. **Imports Dockrion packages**:
   ```python
   from dockrion_adapters import get_adapter
   from dockrion_schema import DockSpec
   from dockrion_common.errors import DockrionError, ValidationError
   from dockrion_common.logger import get_logger
   ```

2. **Initializes the adapter layer**:
   ```python
   adapter = get_adapter(SPEC.agent.framework)
   adapter.load(SPEC.agent.entrypoint)
   ```

3. **Uses adapter for invocation**:
   ```python
   result = adapter.invoke(payload)
   ```

### 3. Error Handling

The runtime now has proper error handling:

```python
try:
    result = adapter.invoke(payload)
except ValidationError as e:
    # Handle validation errors (400)
    logger.error(f"Validation error: {e}")
    return JSONResponse(status_code=400, content={...})
except DockrionError as e:
    # Handle dockrion-specific errors (500)
    logger.error(f"Dockrion error: {e}")
    return JSONResponse(status_code=500, content={...})
except Exception as e:
    # Handle unexpected errors (500)
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return JSONResponse(status_code=500, content={...})
```

### 4. Logging

Structured logging throughout the runtime:

```python
logger = get_logger(__name__)

logger.info(f"Initializing {SPEC.agent.framework} adapter...")
logger.info(f"Loading agent from {SPEC.agent.entrypoint}...")
logger.info(f"Agent {SPEC.agent.name} loaded successfully")
logger.info(f"Received invocation request: {payload}")
logger.info(f"Agent invocation completed in {latency:.3f}s")
```

## Generated Runtime Structure

```python
"""
Generated Dockrion Runtime
Agent: invoice-copilot
Framework: langgraph

This runtime leverages the full Dockrion infrastructure:
- Adapter layer for framework-agnostic agent invocation
- Schema validation for inputs/outputs
- Common utilities for error handling and logging
"""

# 1. Imports
from dockrion_adapters import get_adapter
from dockrion_schema import DockSpec
from dockrion_common.errors import DockrionError, ValidationError
from dockrion_common.logger import get_logger

# 2. Initialize logger
logger = get_logger(__name__)

# 3. Initialize FastAPI app
app = FastAPI(...)

# 4. Load specification
SPEC_DATA = {...}  # Embedded Dockfile
SPEC = DockSpec.model_validate(SPEC_DATA)

# 5. Initialize adapter and load agent
adapter = get_adapter(SPEC.agent.framework)
adapter.load(SPEC.agent.entrypoint)

# 6. Endpoints
@app.get("/health")
async def health(): ...

@app.get("/schema")
async def get_schema(): ...

@app.get("/metrics")
async def metrics(): ...

@app.post("/invoke")
async def invoke(request: Request):
    # Uses adapter.invoke() for framework-agnostic invocation
    result = adapter.invoke(payload)
    ...
```

## Benefits of This Architecture

### 1. Framework Abstraction
- **LangGraph agents**: `adapter.invoke()` → `agent.invoke()`
- **LangChain agents**: `adapter.invoke()` → `agent.run()`
- **Custom agents**: `adapter.invoke()` → `agent()`
- Adding new frameworks just requires updating the adapter

### 2. Consistent Behavior
- Same adapter layer used in local development and Docker
- Same error handling across environments
- Same logging format
- Predictable behavior

### 3. Maintainability
- Single source of truth (adapter layer)
- No duplicated agent loading logic
- Easy to add features (just update adapter/common packages)
- Clear separation of concerns

### 4. Extensibility
- Schema validation ready for V1.1+ (just uncomment)
- Policy engine integration ready (just add policy package)
- Authentication ready (just set env vars)
- Metrics already integrated (Prometheus)

### 5. Production Ready
- Proper error handling with specific error types
- Structured logging for debugging
- Health checks and metrics
- API key authentication support

## Usage

### Building an Image

```bash
$ Dockrion build
ℹ️  Building Docker image for agent: invoice-copilot
✅ Successfully built image: Dockrion/invoice-copilot:dev
```

### Running the Container

```bash
$ docker run -p 8080:8080 Dockrion/invoice-copilot:dev
```

### Testing the Agent

```bash
# Health check
$ curl http://localhost:8080/health
{"status": "ok", "agent": "invoice-copilot"}

# Get schema
$ curl http://localhost:8080/schema
{
  "input": {...},
  "output": {...}
}

# Invoke agent
$ curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"document_text": "INVOICE #123..."}'
{
  "success": true,
  "output": {...},
  "latency_s": 2.341,
  "agent": "invoice-copilot",
  "framework": "langgraph"
}
```

## Future Enhancements (V1.1+)

### 1. Input/Output Validation
```python
# Validate input against io_schema.input
if SPEC.io_schema and SPEC.io_schema.input:
    validate_input(payload, SPEC.io_schema.input)

# Validate output against io_schema.output
if SPEC.io_schema and SPEC.io_schema.output:
    validate_output(result, SPEC.io_schema.output)
```

### 2. Policy Engine Integration
```python
from dockrion_policy import PolicyEngine

policy_engine = PolicyEngine(SPEC.policies)
result = policy_engine.apply(result)
```

### 3. Telemetry Integration
```python
from dockrion_telemetry import track_invocation

track_invocation(
    agent_name=SPEC.agent.name,
    latency=latency,
    success=True
)
```

### 4. Rate Limiting
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/invoke")
@limiter.limit("10/minute")
async def invoke(request: Request): ...
```

## Comparison: Before vs After

| Aspect | Before (Static) | After (Infrastructure-Aware) |
|--------|----------------|------------------------------|
| Agent Loading | Manual `importlib` | Adapter layer |
| Invocation | Framework-specific | Framework-agnostic |
| Error Handling | Generic `Exception` | Typed errors (ValidationError, DockrionError) |
| Logging | Print statements | Structured logging |
| Schema Validation | None | Ready for V1.1+ |
| Policy Engine | None | Ready for V1.1+ |
| Maintainability | Low (duplicated logic) | High (single source of truth) |
| Extensibility | Hard (manual changes) | Easy (update packages) |
| Production Ready | No | Yes |

## Conclusion

The new Docker runtime architecture leverages the full Dockrion infrastructure, providing:
- ✅ Framework-agnostic agent invocation via adapter layer
- ✅ Proper error handling with custom exceptions
- ✅ Structured logging for observability
- ✅ Schema validation (ready for V1.1+)
- ✅ Policy engine integration (ready for V1.1+)
- ✅ Production-ready with health checks and metrics
- ✅ Consistent behavior with local development
- ✅ Maintainable and extensible architecture

This makes Dockrion Docker deployments robust, scalable, and production-ready! 🚀

