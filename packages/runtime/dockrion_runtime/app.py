"""
Dockrion Runtime App Factory

Creates a configured FastAPI application for serving agents.
This is the main entry point that assembles all runtime components.
"""

from contextlib import asynccontextmanager
from typing import Optional, Union

from dockrion_adapters import get_adapter, get_handler_adapter
from dockrion_adapters.base import AgentAdapter
from dockrion_adapters.handler_adapter import HandlerAdapter
from dockrion_common.logger import get_logger
from dockrion_schema import DockSpec
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthContext, AuthError, create_auth_handler
from .config import RuntimeConfig, RuntimeState
from .endpoints import create_health_router, create_info_router, create_invoke_router
from .metrics import RuntimeMetrics
from .openapi import build_security_schemes, configure_openapi_security
from .policies import create_policy_engine
from .schema_utils import create_pydantic_model_from_schema

logger = get_logger(__name__)


def create_app(
    spec: DockSpec,
    agent_entrypoint: Optional[str] = None,
    agent_handler: Optional[str] = None,
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

    # Initialize components
    state.metrics = RuntimeMetrics(config.agent_name)
    state.auth_handler = create_auth_handler(spec.auth.model_dump() if spec.auth else None)
    state.policy_engine = create_policy_engine(
        spec.policies.model_dump() if spec.policies else None
    )

    # Create lifespan manager
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
            adapter: Union[AgentAdapter, HandlerAdapter]
            if config.use_handler_mode:
                adapter = get_handler_adapter()
                state.adapter = adapter
                logger.info("✅ Handler adapter initialized")
                adapter.load(config.agent_handler or "")
                logger.info(f"✅ Handler loaded from {config.agent_handler}")
            else:
                adapter = get_adapter(config.agent_framework)
                state.adapter = adapter
                logger.info(f"✅ {config.agent_framework} adapter initialized")
                adapter.load(config.agent_entrypoint or "")
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
        redoc_url="/redoc",
    )

    # Configure OpenAPI security
    security_schemes = build_security_schemes(config, spec)
    configure_openapi_security(app, security_schemes)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=config.cors_methods,
        allow_headers=["*"],
    )

    # Create auth dependency
    async def verify_auth(request: Request) -> AuthContext:
        """Verify authentication for protected endpoints."""
        assert state.auth_handler is not None, "Auth handler not initialized"
        try:
            return await state.auth_handler.authenticate(request)
        except AuthError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    # Generate dynamic Pydantic models from Dockfile schema
    agent_name_clean = config.agent_name.replace("-", "_").replace(".", "_").capitalize()

    InputModel = create_pydantic_model_from_schema(
        f"{agent_name_clean}Input", spec.io_schema.input if spec.io_schema else None
    )

    OutputModel = create_pydantic_model_from_schema(
        f"{agent_name_clean}Output", spec.io_schema.output if spec.io_schema else None
    )

    # Register routers
    app.include_router(create_health_router(config, state))
    app.include_router(create_info_router(config, spec))
    app.include_router(
        create_invoke_router(
            config, state, verify_auth, input_model=InputModel, output_model=OutputModel
        )
    )

    return app


# Re-export config classes for backwards compatibility
__all__ = ["create_app", "RuntimeConfig", "RuntimeState"]
