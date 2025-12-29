"""
Dockrion Runtime App Factory

Creates a configured FastAPI application for serving agents.
"""

import time
import json
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, AsyncGenerator, Type
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException, Body
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader, HTTPBearer
from fastapi.openapi.models import SecuritySchemeType
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field, create_model

from dockrion_schema import DockSpec
from dockrion_adapters import get_adapter, get_handler_adapter
from dockrion_common.errors import DockrionError, ValidationError
from dockrion_common.logger import get_logger
from dockrion_common.constants import RuntimeDefaults, Timeouts
from dockrion_common.http_models import (
    error_response,
    health_response,
    invoke_response,
    ready_response,
    schema_response,
    info_response,
)

from .auth import create_auth_handler, AuthContext, AuthError
from .policies import RuntimePolicyEngine, create_policy_engine
from .metrics import RuntimeMetrics

logger = get_logger(__name__)


@dataclass
class RuntimeConfig:
    """
    Runtime configuration extracted from DockSpec.
    
    Supports two modes:
    1. **Entrypoint Mode**: Uses framework adapter to load agent with .invoke()
    2. **Handler Mode**: Uses handler adapter to call function directly
    
    All defaults use RuntimeDefaults from dockrion_common.constants
    as the single source of truth.
    """
    # Agent info
    agent_name: str
    agent_framework: str
    agent_description: str = RuntimeDefaults.AGENT_DESCRIPTION
    
    # Invocation mode (entrypoint or handler)
    agent_entrypoint: Optional[str] = None  # Factory → Agent pattern
    agent_handler: Optional[str] = None     # Direct callable pattern
    use_handler_mode: bool = False          # True if handler mode
    
    # Server config (defaults from RuntimeDefaults)
    host: str = RuntimeDefaults.HOST
    port: int = RuntimeDefaults.PORT
    
    # Features
    enable_streaming: bool = False
    timeout_sec: int = Timeouts.REQUEST
    
    # Auth (defaults from RuntimeDefaults)
    auth_enabled: bool = False
    auth_mode: str = RuntimeDefaults.AUTH_MODE
    
    # Metadata
    version: str = RuntimeDefaults.AGENT_VERSION
    
    # CORS (defaults from RuntimeDefaults - converted to list)
    cors_origins: list = field(default_factory=lambda: list(RuntimeDefaults.CORS_ORIGINS))
    cors_methods: list = field(default_factory=lambda: list(RuntimeDefaults.CORS_METHODS))
    
    @property
    def invocation_target(self) -> str:
        """Get the target path for invocation (handler or entrypoint)."""
        return self.agent_handler if self.use_handler_mode else self.agent_entrypoint
    
    @classmethod
    def from_spec(
        cls,
        spec: DockSpec,
        entrypoint_override: Optional[str] = None,
        handler_override: Optional[str] = None
    ) -> "RuntimeConfig":
        """
        Create RuntimeConfig from DockSpec.
        
        Args:
            spec: Validated DockSpec
            entrypoint_override: Override entrypoint from spec
            handler_override: Override handler from spec
            
        Returns:
            RuntimeConfig instance
        """
        agent = spec.agent
        expose = spec.expose
        auth = spec.auth
        metadata = spec.metadata
        
        # Determine mode: handler takes precedence over entrypoint
        handler = handler_override or agent.handler
        entrypoint = entrypoint_override or agent.entrypoint
        use_handler_mode = handler is not None
        
        # arguments is Dict[str, Any] in schema - always a dict
        arguments = spec.arguments if spec.arguments else {}
        
        # Extract timeout from arguments dict (fallback to Timeouts.REQUEST)
        timeout_sec = arguments.get("timeout_sec", Timeouts.REQUEST) if isinstance(arguments, dict) else Timeouts.REQUEST
        
        # cors is Optional[Dict[str, List[str]]] in schema - extract safely
        cors_config = expose.cors if expose and expose.cors else None
        if cors_config and isinstance(cors_config, dict):
            cors_origins = cors_config.get("origins", list(RuntimeDefaults.CORS_ORIGINS))
            cors_methods = cors_config.get("methods", list(RuntimeDefaults.CORS_METHODS))
        else:
            cors_origins = list(RuntimeDefaults.CORS_ORIGINS)
            cors_methods = list(RuntimeDefaults.CORS_METHODS)
        
        return cls(
            agent_name=agent.name,
            agent_framework=agent.framework or RuntimeDefaults.DEFAULT_FRAMEWORK,
            agent_description=agent.description or RuntimeDefaults.AGENT_DESCRIPTION,
            agent_entrypoint=entrypoint,
            agent_handler=handler,
            use_handler_mode=use_handler_mode,
            host=expose.host if expose else RuntimeDefaults.HOST,
            port=expose.port if expose else RuntimeDefaults.PORT,
            enable_streaming=bool(expose and expose.streaming and expose.streaming != "none"),
            timeout_sec=timeout_sec,
            auth_enabled=bool(auth and auth.mode != "none"),
            auth_mode=auth.mode if auth else RuntimeDefaults.AUTH_MODE,
            version=metadata.version if metadata else RuntimeDefaults.AGENT_VERSION,
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
        self.auth_handler = None  # BaseAuthHandler from auth module
        self.policy_engine: Optional[RuntimePolicyEngine] = None
        self.ready: bool = False


def create_app(
    spec: DockSpec,
    agent_entrypoint: Optional[str] = None,
    agent_handler: Optional[str] = None,
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
    
    Supports two modes:
    1. **Entrypoint Mode**: Uses framework adapter (LangGraph, etc.)
    2. **Handler Mode**: Uses direct callable function
    
    Args:
        spec: Validated DockSpec configuration
        agent_entrypoint: Override entrypoint from spec (optional)
        agent_handler: Override handler from spec (optional)
        extra_config: Additional configuration options
        
    Returns:
        Configured FastAPI application
        
    Example:
        >>> # Entrypoint mode (framework agent)
        >>> app = create_app(spec, agent_entrypoint="app.graph:build_graph")
        
        >>> # Handler mode (service function)
        >>> app = create_app(spec, agent_handler="app.service:process_request")
    """
    # Build configuration
    config = RuntimeConfig.from_spec(spec, agent_entrypoint, agent_handler)
    
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
        mode_str = "Handler" if config.use_handler_mode else "Agent"
        target = config.invocation_target
        
        logger.info(f"🚀 Starting Dockrion {mode_str}: {config.agent_name}")
        logger.info(f"   Mode: {'handler' if config.use_handler_mode else 'entrypoint'}")
        logger.info(f"   Framework: {config.agent_framework}")
        logger.info(f"   Target: {target}")
        
        try:
            # Initialize adapter based on mode
            if config.use_handler_mode:
                # Handler mode: use HandlerAdapter
                state.adapter = get_handler_adapter()
                logger.info("✅ Handler adapter initialized")
                state.adapter.load(config.agent_handler)
                logger.info(f"✅ Handler loaded from {config.agent_handler}")
            else:
                # Entrypoint mode: use framework adapter
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
    
    # Build OpenAPI security schemes based on auth configuration
    openapi_security_schemes = {}
    if config.auth_enabled and config.auth_mode == "api_key":
        # Get the header name from auth config
        header_name = "X-API-Key"
        if spec.auth and hasattr(spec.auth, 'api_keys') and spec.auth.api_keys:
            header_name = spec.auth.api_keys.get('header', 'X-API-Key') if isinstance(spec.auth.api_keys, dict) else "X-API-Key"
        
        openapi_security_schemes = {
            "APIKeyHeader": {
                "type": "apiKey",
                "in": "header",
                "name": header_name,
                "description": f"API Key authentication. Pass your API key in the `{header_name}` header."
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "description": "API Key authentication. Pass your API key as a Bearer token in the `Authorization` header."
            }
        }
    elif config.auth_enabled and config.auth_mode == "jwt":
        openapi_security_schemes = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT authentication. Pass your JWT token in the `Authorization` header."
            }
        }
    
    # Create FastAPI app
    app = FastAPI(
        title=config.agent_name,
        description=config.agent_description,
        version=config.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add security schemes to OpenAPI schema
    if openapi_security_schemes:
        def custom_openapi():
            if app.openapi_schema:
                return app.openapi_schema
            
            from fastapi.openapi.utils import get_openapi
            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )
            
            # Add security schemes
            openapi_schema["components"]["securitySchemes"] = openapi_security_schemes
            
            # Apply security to all protected endpoints
            for path, path_item in openapi_schema["paths"].items():
                for method, operation in path_item.items():
                    if method in ["get", "post", "put", "delete", "patch"]:
                        # Skip health and schema endpoints (they're public)
                        if path in ["/health", "/ready", "/schema", "/info"]:
                            continue
                        # Add security requirement to protected endpoints
                        if "APIKeyHeader" in openapi_security_schemes:
                            operation["security"] = [
                                {"APIKeyHeader": []},
                                {"BearerAuth": []}
                            ]
                        else:
                            operation["security"] = [{"BearerAuth": []}]
            
            app.openapi_schema = openapi_schema
            return app.openapi_schema
        
        app.openapi = custom_openapi
    
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
    
    async def verify_auth(request: Request) -> AuthContext:
        """
        Verify authentication for protected endpoints.
        
        Returns:
            AuthContext with identity information
            
        Raises:
            HTTPException: On authentication failure (401/403)
        """
        try:
            return await state.auth_handler.authenticate(request)
        except AuthError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail=e.to_dict()
            )
    
    # =========================================================================
    # Endpoints
    # =========================================================================
    
    @app.get("/health")
    async def health_check():
        """Health check for load balancers and orchestrators."""
        return health_response(
            service=f"runtime:{config.agent_name}",
            version=config.version,
            status="ok",
            agent=config.agent_name,
            framework=config.agent_framework
        )
    
    @app.get("/ready")
    async def readiness_check():
        """Readiness check - verifies agent is fully initialized."""
        if not state.ready or state.adapter is None:
            raise HTTPException(status_code=503, detail="Agent not ready")
        return ready_response(agent=config.agent_name)
    
    @app.get("/schema")
    async def get_schema():
        """Get the input/output schema for this agent."""
        io_schema = spec.io_schema
        return schema_response(
            agent=config.agent_name,
            input_schema=io_schema.input.model_dump() if io_schema and io_schema.input else {},
            output_schema=io_schema.output.model_dump() if io_schema and io_schema.output else {}
        )
    
    @app.get("/info")
    async def get_info():
        """Get agent metadata and configuration."""
        # Build agent info based on invocation mode
        agent_info = {
            "name": config.agent_name,
            "description": config.agent_description,
            "framework": config.agent_framework,
            "mode": "handler" if config.use_handler_mode else "entrypoint",
            "target": config.invocation_target
        }
        
        # Include mode-specific field for clarity
        if config.use_handler_mode:
            agent_info["handler"] = config.agent_handler
        else:
            agent_info["entrypoint"] = config.agent_entrypoint
        
        # Get optional metadata
        metadata = spec.metadata.model_dump() if spec.metadata else None
        
        return info_response(
            agent=agent_info,
            auth_enabled=config.auth_enabled,
            version=config.version,
            metadata=metadata
        )
    
    @app.get("/metrics")
    async def prometheus_metrics():
        """Prometheus metrics endpoint."""
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
    
    # Create Pydantic model for request body validation
    InputModel = _create_pydantic_model_from_schema(
        f"{config.agent_name.replace('-', '_').capitalize()}Input",
        spec.io_schema.input if spec.io_schema else None
    )
    
    @app.post("/invoke")
    async def invoke_agent(
        payload: InputModel = Body(..., description="Agent input payload"),
        auth_context: AuthContext = Depends(verify_auth)
    ):
        """
        Invoke the agent with the given payload.
        
        The adapter layer handles framework-specific invocation logic.
        Request body is automatically validated against the input schema.
        """
        state.metrics.inc_active()
        start_time = time.time()
        
        try:
            # Convert Pydantic model to dict
            payload_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
            
            logger.info("📥 Invoke request received", extra={"payload_keys": list(payload_dict.keys())})
            
            # Note: Pydantic already validated the input schema
            # Additional validation can be done by _validate_input_schema if needed
            
            # Apply input policies
            payload_dict = state.policy_engine.validate_input(payload_dict)
            
            # Invoke agent via adapter
            logger.debug(f"Invoking {config.agent_framework} agent...")
            
            if config.timeout_sec > 0:
                try:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: state.adapter.invoke(payload_dict)
                        ),
                        timeout=config.timeout_sec
                    )
                except asyncio.TimeoutError:
                    raise DockrionError(f"Agent invocation timed out after {config.timeout_sec}s")
            else:
                result = state.adapter.invoke(payload_dict)
            
            # Apply output policies
            result = state.policy_engine.apply_output_policies(result)
            
            latency = time.time() - start_time
            
            # Record metrics
            state.metrics.inc_request("invoke", "success")
            state.metrics.observe_latency("invoke", latency)
            
            logger.info(f"✅ Invoke completed in {latency:.3f}s")
            
            return JSONResponse(invoke_response(
                output=result,
                metadata={
                    "agent": config.agent_name,
                    "framework": config.agent_framework,
                    "latency_seconds": round(latency, 3)
                }
            ))
            
        except ValidationError as e:
            state.metrics.inc_request("invoke", "validation_error")
            logger.warning(f"⚠️ Validation error: {e}")
            return JSONResponse(
                status_code=400,
                content=error_response(e)
            )
            
        except DockrionError as e:
            state.metrics.inc_request("invoke", "dockrion_error")
            logger.error(f"❌ Dockrion error: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(e)
            )
            
        except Exception as e:
            state.metrics.inc_request("invoke", "error")
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=error_response(e)
            )
            
        finally:
            state.metrics.dec_active()
    
    # Streaming endpoint (if enabled)
    if config.enable_streaming:
        @app.post("/invoke/stream")
        async def invoke_agent_stream(
            payload: InputModel = Body(..., description="Agent input payload"),
            auth_context: AuthContext = Depends(verify_auth)
        ):
            """Invoke the agent with streaming response (SSE)."""
            state.metrics.inc_active()
            
            try:
                # Convert Pydantic model to dict
                payload_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
                
                # Apply input policies
                payload_dict = state.policy_engine.validate_input(payload_dict)
                
                async def event_generator() -> AsyncGenerator[str, None]:
                    try:
                        if hasattr(state.adapter, 'invoke_stream'):
                            async for chunk in state.adapter.invoke_stream(payload_dict):
                                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        else:
                            result = state.adapter.invoke(payload_dict)
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


def _create_pydantic_model_from_schema(
    schema_name: str,
    json_schema: Optional[Any]
) -> Type[BaseModel]:
    """
    Create a Pydantic model from JSON Schema definition.
    
    This enables automatic FastAPI request validation and OpenAPI schema generation.
    
    Args:
        schema_name: Name for the generated model
        json_schema: JSON Schema definition (IOSubSchema)
        
    Returns:
        Pydantic BaseModel class
    """
    if not json_schema or not hasattr(json_schema, 'properties'):
        # Return a generic dict model if no schema
        return create_model(
            schema_name,
            __base__=BaseModel,
        )
    
    # Map JSON Schema types to Python types
    type_mapping = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    
    # Build field definitions
    field_definitions = {}
    properties = json_schema.properties if hasattr(json_schema, 'properties') else {}
    required_fields = json_schema.required if hasattr(json_schema, 'required') else []
    
    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue
            
        # Get type
        field_type_str = field_schema.get("type", "string")
        field_type = type_mapping.get(field_type_str, Any)
        
        # Get description
        description = field_schema.get("description", "")
        
        # Determine if required
        is_required = field_name in required_fields
        
        # Create Field with metadata
        if is_required:
            field_definitions[field_name] = (
                field_type,
                Field(..., description=description)
            )
        else:
            field_definitions[field_name] = (
                Optional[field_type],
                Field(None, description=description)
            )
    
    # Create the model
    return create_model(
        schema_name,
        __base__=BaseModel,
        **field_definitions
    )


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

