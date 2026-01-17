"""
Runtime Configuration Classes

Contains RuntimeConfig dataclass for extracting configuration from DockSpec,
and RuntimeState for managing runtime state between lifespan and endpoints.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from dockrion_adapters.base import AgentAdapter
from dockrion_adapters.handler_adapter import HandlerAdapter
from dockrion_common.constants import RuntimeDefaults, StreamingDefaults, Timeouts
from dockrion_schema import DockSpec

from .auth import BaseAuthHandler
from .metrics import RuntimeMetrics
from .policies import RuntimePolicyEngine


@dataclass
class StreamingRuntimeConfig:
    """
    Streaming-specific runtime configuration.

    Extracted from DockSpec.streaming for easy access.
    """

    enabled: bool = False
    async_runs: bool = True
    backend: str = StreamingDefaults.BACKEND_MEMORY
    heartbeat_interval: int = StreamingDefaults.HEARTBEAT_INTERVAL
    max_run_duration: int = StreamingDefaults.MAX_RUN_DURATION
    default_timeout: int = StreamingDefaults.DEFAULT_TIMEOUT
    max_subscribers: int = StreamingDefaults.MAX_SUBSCRIBERS
    allow_client_ids: bool = True

    # Events filter configuration (allow-list or preset)
    events_allowed: Optional[Union[List[str], str]] = None

    # Redis settings (only used if backend == "redis")
    redis_url: Optional[str] = None
    redis_ttl: int = StreamingDefaults.STREAM_TTL
    redis_max_events: int = StreamingDefaults.MAX_EVENTS_PER_RUN
    redis_pool_size: int = StreamingDefaults.CONNECTION_POOL_SIZE

    # Cached EventsFilter instance
    _events_filter: Optional[Any] = field(default=None, repr=False)

    def get_events_filter(self) -> Optional[Any]:
        """
        Get or create the EventsFilter instance.

        Returns:
            EventsFilter instance if dockrion_events is available, None otherwise

        Raises:
            ValueError: If events_allowed config is invalid
        """
        if self._events_filter is not None:
            return self._events_filter

        try:
            from dockrion_events import EventsFilter

            self._events_filter = EventsFilter(self.events_allowed)
            return self._events_filter
        except ImportError:
            return None
        except ValueError:
            # Re-raise validation errors
            raise


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
    agent_handler: Optional[str] = None  # Direct callable pattern
    use_handler_mode: bool = False  # True if handler mode

    # Server config (defaults from RuntimeDefaults)
    host: str = RuntimeDefaults.HOST
    port: int = RuntimeDefaults.PORT

    # Features
    enable_streaming: bool = False
    enable_async_runs: bool = False
    timeout_sec: int = Timeouts.REQUEST

    # Streaming configuration
    streaming: StreamingRuntimeConfig = field(default_factory=StreamingRuntimeConfig)

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
        target = self.agent_handler if self.use_handler_mode else self.agent_entrypoint
        if target is None:
            raise ValueError("No invocation target configured (missing handler or entrypoint)")
        return target

    @classmethod
    def from_spec(
        cls,
        spec: DockSpec,
        entrypoint_override: Optional[str] = None,
        handler_override: Optional[str] = None,
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
        timeout_sec = (
            arguments.get("timeout_sec", Timeouts.REQUEST)
            if isinstance(arguments, dict)
            else Timeouts.REQUEST
        )

        # cors is Optional[Dict[str, List[str]]] in schema - extract safely
        cors_config = expose.cors if expose and expose.cors else None
        if cors_config and isinstance(cors_config, dict):
            cors_origins = cors_config.get("origins", list(RuntimeDefaults.CORS_ORIGINS))
            cors_methods = cors_config.get("methods", list(RuntimeDefaults.CORS_METHODS))
        else:
            cors_origins = list(RuntimeDefaults.CORS_ORIGINS)
            cors_methods = list(RuntimeDefaults.CORS_METHODS)

        # Extract streaming configuration
        streaming_config = StreamingRuntimeConfig()
        enable_streaming = bool(expose and expose.streaming and expose.streaming != "none")
        enable_async_runs = False

        if spec.streaming:
            streaming = spec.streaming
            streaming_config = StreamingRuntimeConfig(
                enabled=True,
                async_runs=streaming.async_runs,
                backend=streaming.backend,
                allow_client_ids=streaming.allow_client_ids,
            )
            enable_async_runs = streaming.async_runs

            # Events config
            if streaming.events:
                streaming_config.heartbeat_interval = streaming.events.heartbeat_interval
                streaming_config.max_run_duration = streaming.events.max_run_duration
                # Extract allow-list configuration for events filter
                streaming_config.events_allowed = streaming.events.allowed

            # Connection config
            if streaming.connection:
                streaming_config.default_timeout = streaming.connection.default_timeout
                streaming_config.max_subscribers = streaming.connection.max_subscribers_per_run

            # Redis config
            if streaming.backend == "redis" and streaming.redis:
                streaming_config.redis_url = streaming.redis.url
                streaming_config.redis_ttl = streaming.redis.stream_ttl_seconds
                streaming_config.redis_max_events = streaming.redis.max_events_per_run
                streaming_config.redis_pool_size = streaming.redis.connection_pool_size

        return cls(
            agent_name=agent.name,
            agent_framework=agent.framework or RuntimeDefaults.DEFAULT_FRAMEWORK,
            agent_description=agent.description or RuntimeDefaults.AGENT_DESCRIPTION,
            agent_entrypoint=entrypoint,
            agent_handler=handler,
            use_handler_mode=use_handler_mode,
            host=expose.host if expose else RuntimeDefaults.HOST,
            port=expose.port if expose else RuntimeDefaults.PORT,
            enable_streaming=enable_streaming,
            enable_async_runs=enable_async_runs,
            streaming=streaming_config,
            timeout_sec=timeout_sec,
            auth_enabled=bool(auth and auth.mode != "none"),
            auth_mode=auth.mode if auth else RuntimeDefaults.AUTH_MODE,
            version=metadata.version
            if metadata and metadata.version
            else RuntimeDefaults.AGENT_VERSION,
            cors_origins=cors_origins,
            cors_methods=cors_methods,
        )


class RuntimeState:
    """
    Holds runtime state (adapter, spec, etc.).

    Used to share state between lifespan and endpoints.
    """

    def __init__(self) -> None:
        self.adapter: Optional[Union[AgentAdapter, HandlerAdapter]] = None
        self.spec: Optional[DockSpec] = None
        self.config: Optional[RuntimeConfig] = None
        self.metrics: Optional[RuntimeMetrics] = None
        self.auth_handler: Optional[BaseAuthHandler] = None
        self.policy_engine: Optional[RuntimePolicyEngine] = None
        self.ready: bool = False

        # Streaming components (initialized if streaming enabled)
        self.event_bus: Optional[Any] = None  # EventBus
        self.run_manager: Optional[Any] = None  # RunManager
