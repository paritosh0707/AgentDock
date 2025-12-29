"""
Runtime Configuration Classes

Contains RuntimeConfig dataclass for extracting configuration from DockSpec,
and RuntimeState for managing runtime state between lifespan and endpoints.
"""

from dataclasses import dataclass, field
from typing import Optional, Union

from dockrion_adapters.base import AgentAdapter
from dockrion_adapters.handler_adapter import HandlerAdapter
from dockrion_common.constants import RuntimeDefaults, Timeouts
from dockrion_schema import DockSpec

from .auth import BaseAuthHandler
from .metrics import RuntimeMetrics
from .policies import RuntimePolicyEngine


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
