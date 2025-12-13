"""
Dockrion Runtime App Factory

Creates a configured FastAPI application for serving agents.
"""

import time
import json
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from dockrion_schema import DockSpec
from dockrion_adapters import get_adapter
from dockrion_common.errors import DockrionError, ValidationError
from dockrion_common.logger import get_logger

from .auth import AuthHandler, create_auth_handler
from .policies import RuntimePolicyEngine, create_policy_engine
from .metrics import RuntimeMetrics

logger = get_logger(__name__)


@dataclass
class RuntimeConfig:
    """
    Runtime configuration extracted from DockSpec.
    
    Provides easy access to configuration values with defaults.
    """
    # Agent info
    agent_name: str
    agent_framework: str
    agent_entrypoint: str
    agent_description: str = "Dockrion Agent"
    
    # Server config
    host: str = "0.0.0.0"
    port: int = 8080
    
    # Features
    enable_streaming: bool = False
    timeout_sec: int = 30
    
    # Auth
    auth_enabled: bool = False
    auth_mode: str = "none"
    
    # Metadata
    version: str = "1.0.0"
    
    # CORS (as dict for flexibility)
    cors_origins: list = field(default_factory=lambda: ["*"])
    cors_methods: list = field(default_factory=lambda: ["*"])
    
    @classmethod
    def from_spec(cls, spec: DockSpec, entrypoint_override: Optional[str] = None) -> "RuntimeConfig":
        """
        Create RuntimeConfig from DockSpec.
        
        Args:
            spec: Validated DockSpec
            entrypoint_override: Override entrypoint from spec
            
        Returns:
            RuntimeConfig instance
        """
        agent = spec.agent
        expose = spec.expose
        auth = spec.auth
        metadata = spec.metadata
        
        # arguments is Dict[str, Any] in schema - always a dict
        arguments = spec.arguments if spec.arguments else {}
        
        # Extract timeout from arguments dict
        timeout_sec = arguments.get("timeout_sec", 30) if isinstance(arguments, dict) else 30
        
        # cors is Optional[Dict[str, List[str]]] in schema - extract safely
        cors_config = expose.cors if expose and expose.cors else None
        if cors_config and isinstance(cors_config, dict):
            cors_origins = cors_config.get("origins", ["*"])
            cors_methods = cors_config.get("methods", ["*"])
        else:
            cors_origins = ["*"]
            cors_methods = ["*"]
        
        return cls(
            agent_name=agent.name,
            agent_framework=agent.framework,
            agent_entrypoint=entrypoint_override or agent.entrypoint,
            agent_description=agent.description or "Dockrion Agent",
            host=expose.host if expose else "0.0.0.0",
            port=expose.port if expose else 8080,
            enable_streaming=bool(expose and expose.streaming and expose.streaming != "none"),
            timeout_sec=timeout_sec,
            auth_enabled=bool(auth and auth.mode != "none"),
            auth_mode=auth.mode if auth else "none",
            version=metadata.version if metadata else "1.0.0",
            cors_origins=cors_origins,
            cors_methods=cors_methods,
        )


class RuntimeState:
    """
    Holds runtime state (adapter, spec, etc.).
    
    Used to share state between lifespan and endpoints.
    """
    
    def __init__(self):
        self.adapter = None
        self.spec: Optional[DockSpec] = None
        self.config: Optional[RuntimeConfig] = None
        self.metrics: Optional[RuntimeMetrics] = None
        self.auth_handler: Optional[AuthHandler] = None
        self.policy_engine: Optional[RuntimePolicyEngine] = None
        self.ready: bool = False


def create_app(
    spec: DockSpec,
    agent_entrypoint: Optional[str] = None,
    extra_config: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """
    Create a FastAPI application for serving an agent.
    
    This is the main entry point for the runtime. It creates a fully
    configured FastAPI app with:
    - Health/readiness endpoints
    - Invoke endpoint (sync and streaming)
    - Schema/info endpoints
    - Prometheus metrics
    - Authentication
    - Policy enforcement
    
    Args:
        spec: Validated DockSpec configuration
        agent_entrypoint: Override entrypoint from spec (optional)
        extra_config: Additional configuration options
        
    Returns:
        Configured FastAPI application
        
    Example:
        >>> from dockrion_schema import DockSpec
        >>> spec = DockSpec.model_validate(spec_data)
        >>> app = create_app(spec)
        >>> # Run with: uvicorn.run(app, host="0.0.0.0", port=8080)
    """
    # Build configuration
    config = RuntimeConfig.from_spec(spec, agent_entrypoint)
    
    # Create shared state
    state = RuntimeState()
    state.spec = spec
    state.config = config
    
    # Create components
    state.metrics = RuntimeMetrics(config.agent_name)
    state.auth_handler = create_auth_handler(
        spec.auth.model_dump() if spec.auth else None
    )
    state.policy_engine = create_policy_engine(
        spec.policies.model_dump() if spec.policies else None
    )
    
    # Lifespan manager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle."""
        logger.info(f"🚀 Starting Dockrion Agent: {config.agent_name}")
        logger.info(f"   Framework: {config.agent_framework}")
        logger.info(f"   Entrypoint: {config.agent_entrypoint}")
        
        try:
            # Initialize adapter and load agent
            state.adapter = get_adapter(config.agent_framework)
            logger.info(f"✅ {config.agent_framework} adapter initialized")
            
            state.adapter.load(config.agent_entrypoint)
            logger.info(f"✅ Agent loaded from {config.agent_entrypoint}")
            
            state.ready = True
            logger.info(f"🎯 Agent {config.agent_name} ready on {config.host}:{config.port}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            raise
        
        yield
        
        logger.info(f"👋 Shutting down agent: {config.agent_name}")
    
    # Create FastAPI app
    app = FastAPI(
        title=config.agent_name,
        description=config.agent_description,
        version=config.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=config.cors_methods,
        allow_headers=["*"],
    )
    
    # =========================================================================
    # Dependency: Auth verification
    # =========================================================================
    
    async def verify_auth(request: Request) -> Optional[str]:
        """Verify authentication for protected endpoints."""
        return await state.auth_handler.verify(request)
    
    # =========================================================================
    # Endpoints
    # =========================================================================
    
    @app.get("/health")
    async def health_check():
        """Health check for load balancers and orchestrators."""
        return {
            "status": "healthy",
            "agent": config.agent_name,
            "framework": config.agent_framework,
            "version": config.version
        }
    
    @app.get("/ready")
    async def readiness_check():
        """Readiness check - verifies agent is fully initialized."""
        if not state.ready or state.adapter is None:
            raise HTTPException(status_code=503, detail="Agent not ready")
        return {"status": "ready", "agent": config.agent_name}
    
    @app.get("/schema")
    async def get_schema():
        """Get the input/output schema for this agent."""
        io_schema = spec.io_schema
        return {
            "agent": config.agent_name,
            "input_schema": io_schema.input.model_dump() if io_schema and io_schema.input else {},
            "output_schema": io_schema.output.model_dump() if io_schema and io_schema.output else {}
        }
    
    @app.get("/info")
    async def get_info():
        """Get agent metadata and configuration."""
        info = {
            "agent": {
                "name": config.agent_name,
                "description": config.agent_description,
                "framework": config.agent_framework,
                "entrypoint": config.agent_entrypoint
            },
            "auth_enabled": config.auth_enabled,
            "version": config.version
        }
        
        if spec.model:
            info["model"] = {
                "provider": spec.model.provider,
                "name": spec.model.name
            }
        
        if spec.metadata:
            info["metadata"] = spec.metadata.model_dump()
        
        return info
    
    @app.get("/metrics")
    async def prometheus_metrics():
        """Prometheus metrics endpoint."""
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
    
    @app.post("/invoke")
    async def invoke_agent(
        request: Request,
        api_key: Optional[str] = Depends(verify_auth)
    ):
        """
        Invoke the agent with the given payload.
        
        The adapter layer handles framework-specific invocation logic.
        """
        state.metrics.inc_active()
        start_time = time.time()
        
        try:
            # Parse request payload
            try:
                payload = await request.json()
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON payload")
            
            logger.info("📥 Invoke request received", extra={"payload_keys": list(payload.keys())})
            
            # Validate input schema if defined
            _validate_input_schema(payload, spec.io_schema)
            
            # Apply input policies
            payload = state.policy_engine.validate_input(payload)
            
            # Invoke agent via adapter
            logger.debug(f"Invoking {config.agent_framework} agent...")
            
            if config.timeout_sec > 0:
                try:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: state.adapter.invoke(payload)
                        ),
                        timeout=config.timeout_sec
                    )
                except asyncio.TimeoutError:
                    raise DockrionError(f"Agent invocation timed out after {config.timeout_sec}s")
            else:
                result = state.adapter.invoke(payload)
            
            # Apply output policies
            result = state.policy_engine.apply_output_policies(result)
            
            latency = time.time() - start_time
            
            # Record metrics
            state.metrics.inc_request("invoke", "success")
            state.metrics.observe_latency("invoke", latency)
            
            logger.info(f"✅ Invoke completed in {latency:.3f}s")
            
            return JSONResponse({
                "success": True,
                "output": result,
                "metadata": {
                    "agent": config.agent_name,
                    "framework": config.agent_framework,
                    "latency_seconds": round(latency, 3)
                }
            })
            
        except ValidationError as e:
            state.metrics.inc_request("invoke", "validation_error")
            logger.warning(f"⚠️ Validation error: {e}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": str(e), "error_type": "ValidationError"}
            )
            
        except DockrionError as e:
            state.metrics.inc_request("invoke", "dockrion_error")
            logger.error(f"❌ Dockrion error: {e}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e), "error_type": "DockrionError"}
            )
            
        except Exception as e:
            state.metrics.inc_request("invoke", "error")
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e), "error_type": type(e).__name__}
            )
            
        finally:
            state.metrics.dec_active()
    
    # Streaming endpoint (if enabled)
    if config.enable_streaming:
        @app.post("/invoke/stream")
        async def invoke_agent_stream(
            request: Request,
            api_key: Optional[str] = Depends(verify_auth)
        ):
            """Invoke the agent with streaming response (SSE)."""
            state.metrics.inc_active()
            
            try:
                payload = await request.json()
                
                # Validate
                _validate_input_schema(payload, spec.io_schema)
                payload = state.policy_engine.validate_input(payload)
                
                async def event_generator() -> AsyncGenerator[str, None]:
                    try:
                        if hasattr(state.adapter, 'invoke_stream'):
                            async for chunk in state.adapter.invoke_stream(payload):
                                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        else:
                            result = state.adapter.invoke(payload)
                            yield f"data: {json.dumps({'output': result})}\n\n"
                        
                        yield f"data: {json.dumps({'done': True})}\n\n"
                        
                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    finally:
                        state.metrics.dec_active()
                
                return StreamingResponse(
                    event_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
                
            except Exception as e:
                state.metrics.dec_active()
                raise HTTPException(status_code=500, detail=str(e))
    
    return app


def _validate_input_schema(payload: Dict[str, Any], io_schema) -> None:
    """
    Validate input payload against schema.
    
    Args:
        payload: Input dictionary
        io_schema: IOSchema from DockSpec
        
    Raises:
        ValidationError: If validation fails
    """
    if not io_schema or not io_schema.input:
        return
    
    input_schema = io_schema.input
    
    # Check required fields
    if input_schema.required:
        missing = [f for f in input_schema.required if f not in payload]
        if missing:
            raise ValidationError(f"Missing required fields: {missing}")
    
    # Type validation
    if input_schema.properties:
        props = input_schema.properties
        for field_name, value in payload.items():
            if field_name in props:
                expected_type = props[field_name].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    raise ValidationError(f"Field '{field_name}' must be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    raise ValidationError(f"Field '{field_name}' must be a number")
                elif expected_type == "array" and not isinstance(value, list):
                    raise ValidationError(f"Field '{field_name}' must be an array")
                elif expected_type == "object" and not isinstance(value, dict):
                    raise ValidationError(f"Field '{field_name}' must be an object")

