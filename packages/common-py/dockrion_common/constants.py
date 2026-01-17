"""
dockrion Shared Constants

This module defines constants used across multiple dockrion packages and services.
It serves as the single source of truth for supported values, defaults, and configuration.

All constants are organized into namespaced frozen dataclasses for:
- Type safety and IDE autocomplete
- Immutability (frozen=True prevents modification)
- Clear organization by domain

Usage:
    from dockrion_common.constants import (
        RuntimeDefaults,
        ServicePorts,
        Timeouts,
        SupportedValues,
        Patterns,
    )

    port = RuntimeDefaults.PORT
    timeout = Timeouts.INVOCATION

    if framework not in SupportedValues.FRAMEWORKS:
        raise ValidationError(f"Unsupported framework: {framework}")
"""

from dataclasses import dataclass
from typing import Tuple

# =============================================================================
# VERSION INFORMATION
# =============================================================================


@dataclass(frozen=True)
class _VersionInfo:
    """Version information for dockrion platform."""

    PLATFORM: str = "1.0"
    API: str = "v1"
    DOCKFILE_SUPPORTED: Tuple[str, ...] = ("1.0",)


VersionInfo = _VersionInfo()

# Convenience aliases for version info
DOCKRION_VERSION = VersionInfo.PLATFORM
API_VERSION = VersionInfo.API
SUPPORTED_DOCKFILE_VERSIONS = list(VersionInfo.DOCKFILE_SUPPORTED)


# =============================================================================
# SUPPORTED VALUES
# =============================================================================


@dataclass(frozen=True)
class _SupportedValues:
    """Supported values for various configuration options."""

    FRAMEWORKS: Tuple[str, ...] = ("langgraph", "langchain", "custom")
    AUTH_MODES: Tuple[str, ...] = ("none", "api_key", "jwt", "oauth2")
    STREAMING_MODES: Tuple[str, ...] = ("sse", "websocket", "none")
    LOG_LEVELS: Tuple[str, ...] = ("debug", "info", "warn", "error")

    PERMISSIONS: Tuple[str, ...] = (
        "deploy",  # Deploy new agents
        "rollback",  # Rollback to previous versions
        "invoke",  # Invoke agents
        "view_metrics",  # View metrics and telemetry
        "key_manage",  # Manage API keys
        "read_logs",  # Read agent logs
        "read_docs",  # Read documentation
    )


SupportedValues = _SupportedValues()

# Convenience aliases for supported values
SUPPORTED_FRAMEWORKS = list(SupportedValues.FRAMEWORKS)
SUPPORTED_AUTH_MODES = list(SupportedValues.AUTH_MODES)
SUPPORTED_STREAMING = list(SupportedValues.STREAMING_MODES)
LOG_LEVELS = list(SupportedValues.LOG_LEVELS)
PERMISSIONS = list(SupportedValues.PERMISSIONS)


# =============================================================================
# RUNTIME DEFAULTS
# =============================================================================


@dataclass(frozen=True)
class _RuntimeDefaults:
    """
    Centralized runtime configuration defaults.

    This is the single source of truth for runtime defaults.
    All packages should import and use these values.

    Usage:
        from dockrion_common.constants import RuntimeDefaults

        port = spec.expose.port or RuntimeDefaults.PORT
        host = RuntimeDefaults.HOST
    """

    # Network
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # Streaming
    STREAMING: str = "sse"

    # Auth
    AUTH_MODE: str = "none"

    # CORS (permissive by default for runtime)
    CORS_ORIGINS: Tuple[str, ...] = ("*",)
    CORS_METHODS: Tuple[str, ...] = ("*",)

    # Development CORS (specific origins for UI dev servers)
    DEV_CORS_ORIGINS: Tuple[str, ...] = ("http://localhost:3000", "http://localhost:5173")
    DEV_CORS_METHODS: Tuple[str, ...] = ("GET", "POST", "PUT", "DELETE", "OPTIONS")

    # Versioning
    AGENT_VERSION: str = "1.0.0"

    # Framework
    DEFAULT_FRAMEWORK: str = "custom"

    # Agent defaults
    AGENT_DESCRIPTION: str = "Dockrion Agent"

    # Log level
    LOG_LEVEL: str = "info"

    # Rate limiting
    RATE_LIMIT: str = "100/m"


RuntimeDefaults = _RuntimeDefaults()


# =============================================================================
# SERVICE PORTS
# =============================================================================


@dataclass(frozen=True)
class _ServicePorts:
    """
    Default ports for dockrion services.

    Usage:
        from dockrion_common.constants import ServicePorts

        controller_port = ServicePorts.CONTROLLER
    """

    CONTROLLER: int = 5001
    AUTH: int = 5002
    BUILDER: int = 5003
    RUNTIME: int = 8080
    DASHBOARD_BFF: int = 4000


ServicePorts = _ServicePorts()


# =============================================================================
# TIMEOUTS
# =============================================================================


@dataclass(frozen=True)
class _Timeouts:
    """
    Default timeout values in seconds.

    Usage:
        from dockrion_common.constants import Timeouts

        timeout = Timeouts.INVOCATION
    """

    REQUEST: int = 30
    BUILD: int = 600  # 10 minutes
    INVOCATION: int = 120  # 2 minutes


Timeouts = _Timeouts()


# =============================================================================
# SERVICE NAMES
# =============================================================================


@dataclass(frozen=True)
class _ServiceNames:
    """
    Standard service names for dockrion platform.

    Usage:
        from dockrion_common.constants import ServiceNames

        service = ServiceNames.CONTROLLER
    """

    CONTROLLER: str = "controller"
    AUTH: str = "auth"
    BUILDER: str = "builder"
    RUNTIME: str = "runtime-gateway"
    DASHBOARD_BFF: str = "dashboard-bff"


ServiceNames = _ServiceNames()


# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================


@dataclass(frozen=True)
class _EnvVars:
    """
    Standard environment variable names.

    Usage:
        from dockrion_common.constants import EnvVars
        import os

        api_key = os.getenv(EnvVars.API_KEY)
    """

    LANGFUSE_PUBLIC: str = "LANGFUSE_PUBLIC"
    LANGFUSE_SECRET: str = "LANGFUSE_SECRET"
    API_KEY: str = "DOCKRION_API_KEY"
    CONTROLLER_URL: str = "DOCKRION_CONTROLLER_URL"
    AUTH_URL: str = "DOCKRION_AUTH_URL"
    BUILDER_URL: str = "DOCKRION_BUILDER_URL"


EnvVars = _EnvVars()


# =============================================================================
# VALIDATION PATTERNS
# =============================================================================


@dataclass(frozen=True)
class _Patterns:
    """
    Validation regex patterns.

    Usage:
        from dockrion_common.constants import Patterns
        import re

        if not re.match(Patterns.AGENT_NAME, name):
            raise ValidationError("Invalid agent name")
    """

    AGENT_NAME: str = r"^[a-z0-9-]+$"
    ENTRYPOINT: str = r"^[\w\.]+:\w+$"
    HANDLER: str = r"^[\w\.]+:\w+$"
    RATE_LIMIT: str = r"^(\d+)/(s|m|h|d)$"


Patterns = _Patterns()


# =============================================================================
# STREAMING DEFAULTS
# =============================================================================


@dataclass(frozen=True)
class _StreamingDefaults:
    """
    Centralized streaming configuration defaults.

    This is the single source of truth for streaming defaults.
    All packages should import and use these values.

    Usage:
        from dockrion_common.constants import StreamingDefaults

        heartbeat = StreamingDefaults.HEARTBEAT_INTERVAL
        timeout = StreamingDefaults.DEFAULT_TIMEOUT
    """

    # Event configuration
    HEARTBEAT_INTERVAL: int = 15  # seconds
    MAX_RUN_DURATION: int = 3600  # 1 hour

    # Connection settings
    DEFAULT_TIMEOUT: int = 300  # 5 minutes
    MAX_SUBSCRIBERS: int = 100

    # Backend settings
    STREAM_TTL: int = 3600  # 1 hour event retention
    MAX_EVENTS_PER_RUN: int = 1000
    CONNECTION_POOL_SIZE: int = 10

    # Backend types
    BACKEND_MEMORY: str = "memory"
    BACKEND_REDIS: str = "redis"

    # ID generator types
    ID_GENERATOR_UUID: str = "uuid"
    ID_GENERATOR_CUSTOM: str = "custom"


StreamingDefaults = _StreamingDefaults()


# =============================================================================
# HTTP STATUS CODES
# =============================================================================


@dataclass(frozen=True)
class _HttpStatus:
    """
    HTTP status codes for reference.

    Usage:
        from dockrion_common.constants import HttpStatus

        return JSONResponse(status_code=HttpStatus.OK, content=data)
    """

    # Success
    OK: int = 200
    CREATED: int = 201
    ACCEPTED: int = 202
    NO_CONTENT: int = 204

    # Client errors
    BAD_REQUEST: int = 400
    UNAUTHORIZED: int = 401
    FORBIDDEN: int = 403
    NOT_FOUND: int = 404
    CONFLICT: int = 409
    TOO_MANY_REQUESTS: int = 429

    # Server errors
    INTERNAL_ERROR: int = 500
    SERVICE_UNAVAILABLE: int = 503


HttpStatus = _HttpStatus()
