"""
dockrion Shared Constants

This module defines constants used across multiple dockrion packages and services.
It serves as the single source of truth for supported values, defaults, and configuration.

Usage:
    from dockrion_common.constants import SUPPORTED_FRAMEWORKS, PERMISSIONS
    
    if framework not in SUPPORTED_FRAMEWORKS:
        raise ValidationError(f"Unsupported framework: {framework}")
"""

# =============================================================================
# VERSION INFORMATION
# =============================================================================

DOCKRION_VERSION = "1.0"
"""Current dockrion platform version"""

SUPPORTED_DOCKFILE_VERSIONS = ["1.0"]
"""List of supported Dockfile specification versions"""

API_VERSION = "v1"
"""Current API version for REST endpoints"""


# =============================================================================
# SUPPORTED VALUES (Must match schema definitions)
# =============================================================================

SUPPORTED_FRAMEWORKS = ["langgraph", "langchain", "custom"]
"""Agent frameworks supported by dockrion. 'custom' is for handler-based agents."""

HANDLER_PATTERN = r"^[\w\.]+:\w+$"
"""Regex pattern for valid handler format (module:callable)"""

SUPPORTED_PROVIDERS = [
    "openai",
    "azure",
    "anthropic",
    "google",
    "ollama",
    "custom"
]
"""LLM providers supported by dockrion"""

SUPPORTED_AUTH_MODES = ["none", "api_key", "jwt", "oauth2"]
"""Authentication modes supported by dockrion (none = disabled)"""

SUPPORTED_STREAMING = ["sse", "websocket", "none"]
"""Streaming modes for agent responses"""

LOG_LEVELS = ["debug", "info", "warn", "error"]
"""Valid log levels for observability configuration"""


# =============================================================================
# PERMISSIONS
# =============================================================================

PERMISSIONS = [
    "deploy",           # Deploy new agents
    "rollback",         # Rollback to previous versions
    "invoke",           # Invoke agents
    "view_metrics",     # View metrics and telemetry
    "key_manage",       # Manage API keys
    "read_logs",        # Read agent logs
    "read_docs",        # Read documentation
]
"""Available permissions for role-based access control"""


# =============================================================================
# DEFAULT VALUES
# =============================================================================

# Service Ports (for local development)
DEFAULT_CONTROLLER_PORT = 5001
"""Default port for Controller service"""

DEFAULT_AUTH_PORT = 5002
"""Default port for Auth service"""

DEFAULT_BUILDER_PORT = 5003
"""Default port for Builder service"""

DEFAULT_RUNTIME_PORT = 8080
"""Default port for Runtime Gateway"""

DEFAULT_DASHBOARD_BFF_PORT = 4000
"""Default port for Dashboard BFF"""

# Runtime Defaults
DEFAULT_HOST = "0.0.0.0"
"""Default host for service binding"""

DEFAULT_PORT = 8080
"""Default port for agent runtime"""

DEFAULT_LOG_LEVEL = "info"
"""Default logging level"""

# Timeouts (seconds)
DEFAULT_REQUEST_TIMEOUT = 30
"""Default timeout for HTTP requests"""

DEFAULT_BUILD_TIMEOUT = 600
"""Default timeout for Docker image builds (10 minutes)"""

DEFAULT_INVOCATION_TIMEOUT = 120
"""Default timeout for agent invocations (2 minutes)"""

# Rate Limiting
DEFAULT_RATE_LIMIT = "100/m"
"""Default rate limit (100 requests per minute)"""

# API Configuration
DEFAULT_CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
"""Default CORS origins for local development"""

DEFAULT_CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
"""Default CORS methods"""


# =============================================================================
# ENVIRONMENT VARIABLE NAMES
# =============================================================================

ENV_LANGFUSE_PUBLIC = "LANGFUSE_PUBLIC"
"""Environment variable for Langfuse public key"""

ENV_LANGFUSE_SECRET = "LANGFUSE_SECRET"
"""Environment variable for Langfuse secret key"""

ENV_API_KEY = "DOCKRION_API_KEY"
"""Environment variable for dockrion API key"""

ENV_CONTROLLER_URL = "DOCKRION_CONTROLLER_URL"
"""Environment variable for Controller service URL"""

ENV_AUTH_URL = "DOCKRION_AUTH_URL"
"""Environment variable for Auth service URL"""

ENV_BUILDER_URL = "DOCKRION_BUILDER_URL"
"""Environment variable for Builder service URL"""


# =============================================================================
# SERVICE NAMES
# =============================================================================

SERVICE_CONTROLLER = "controller"
"""Controller service name"""

SERVICE_AUTH = "auth"
"""Auth service name"""

SERVICE_BUILDER = "builder"
"""Builder service name"""

SERVICE_RUNTIME = "runtime-gateway"
"""Runtime Gateway service name"""

SERVICE_DASHBOARD_BFF = "dashboard-bff"
"""Dashboard BFF service name"""


# =============================================================================
# VALIDATION PATTERNS
# =============================================================================

AGENT_NAME_PATTERN = r"^[a-z0-9-]+$"
"""Regex pattern for valid agent names (lowercase alphanumeric with hyphens)"""

ENTRYPOINT_PATTERN = r"^[\w\.]+:\w+$"
"""Regex pattern for valid entrypoint format (module:callable)"""

RATE_LIMIT_PATTERN = r"^(\d+)/(s|m|h|d)$"
"""Regex pattern for rate limit format (e.g., 1000/m)"""


# =============================================================================
# HTTP STATUS CODES (for reference)
# =============================================================================

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_NO_CONTENT = 204

HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_TOO_MANY_REQUESTS = 429

HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503


# =============================================================================
# FUTURE EXTENSIBILITY
# =============================================================================

# Note: When adding new constants for V2+, use versioned naming:
# SUPPORTED_FRAMEWORKS_V2 = ["langgraph", "langchain", "autogen"]
# This prevents breaking V1 consumers

