"""
Dockrion Runtime App Factory

Creates a configured FastAPI application for serving agents.
This is the main entry point that assembles all runtime components.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Union

from dockrion_adapters import get_adapter, get_handler_adapter
from dockrion_adapters.base import AgentAdapter
from dockrion_adapters.handler_adapter import HandlerAdapter
from dockrion_common.logger import get_logger
from dockrion_schema import DockSpec
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth import AuthContext, AuthError, create_auth_handler
from .config import RuntimeConfig, RuntimeState
from .endpoints import (
    create_health_router,
    create_info_router,
    create_invoke_router,
    create_runs_router,
    create_welcome_router,
)
from .metrics import RuntimeMetrics
from .openapi import build_security_schemes, configure_openapi_security
from .policies import create_policy_engine
from .schema_utils import create_pydantic_model_from_schema

logger = get_logger(__name__)

# Check if dockrion_events package is available at import time
_EVENTS_PACKAGE_AVAILABLE = False
try:
    import dockrion_events  # noqa: F401

    _EVENTS_PACKAGE_AVAILABLE = True
except ImportError:
    pass


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

            # Initialize streaming components if enabled
            if config.enable_async_runs or config.streaming.enabled:
                try:
                    from dockrion_events import EventBus, InMemoryBackend, RunManager

                    # Create backend based on configuration
                    if config.streaming.backend == "redis" and config.streaming.redis_url:
                        try:
                            from dockrion_events import RedisBackend

                            backend = RedisBackend(
                                url=config.streaming.redis_url,
                                stream_ttl_seconds=config.streaming.redis_ttl,
                                max_events_per_run=config.streaming.redis_max_events,
                                connection_pool_size=config.streaming.redis_pool_size,
                            )
                            logger.info("✅ Redis backend initialized")
                        except ImportError:
                            logger.warning(
                                "Redis backend requested but redis not installed. "
                                "Falling back to in-memory backend."
                            )
                            backend = InMemoryBackend()
                    else:
                        backend = InMemoryBackend()
                        logger.info("✅ In-memory backend initialized")

                    # Create EventBus and RunManager
                    state.event_bus = EventBus(backend)
                    state.run_manager = RunManager(
                        event_bus=state.event_bus,
                        allow_client_ids=config.streaming.allow_client_ids,
                        agent_name=config.agent_name,
                        framework=config.agent_framework,
                    )
                    logger.info("✅ Streaming components initialized")

                except ImportError as e:
                    logger.warning(
                        f"Streaming components not available: {e}. "
                        "Install dockrion-events for streaming support."
                    )

            state.ready = True
            logger.info(f"🎯 Agent {config.agent_name} ready on {config.host}:{config.port}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            raise

        yield

        # Cleanup streaming components
        if state.event_bus is not None:
            try:
                await state.event_bus.close()
                logger.info("✅ Event bus closed")
            except Exception as e:
                logger.warning(f"Error closing event bus: {e}")

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

    # Determine if output validation should be strict
    # Default to True; False if io_schema.strict is False or output is None
    strict_output = True
    if spec.io_schema:
        # Check strict flag (defaults to True)
        strict_output = getattr(spec.io_schema, "strict", True)
        # Also skip validation if output schema is not defined
        if spec.io_schema.output is None:
            strict_output = False

    # Register routers
    app.include_router(create_welcome_router(config))
    app.include_router(create_health_router(config, state))
    app.include_router(create_info_router(config, spec))
    app.include_router(
        create_invoke_router(
            config,
            state,
            verify_auth,
            input_model=InputModel,
            output_model=OutputModel,
            strict_output_validation=strict_output,
        )
    )

    # Register runs router if async runs are enabled AND events package is available
    if config.enable_async_runs:
        if _EVENTS_PACKAGE_AVAILABLE:
            app.include_router(
                create_runs_router(
                    config,
                    state,
                    verify_auth,
                    input_model=InputModel,
                    output_model=OutputModel,
                )
            )
            logger.info("✅ Async runs endpoints registered (/runs)")
        else:
            logger.warning(
                "Async runs enabled but dockrion-events package not installed. "
                "/runs endpoints will not be available. "
                "Install with: pip install dockrion-events"
            )

    # Mount static files for logo and assets
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


# Re-export config classes for backwards compatibility
__all__ = ["create_app", "RuntimeConfig", "RuntimeState"]
