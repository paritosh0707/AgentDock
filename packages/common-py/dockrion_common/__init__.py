"""
dockrion Common Package

Shared utilities and primitives used across all dockrion packages and services.

This package provides:
- Exception classes for consistent error handling
- Constants for supported values and defaults
- Validation utilities for input checking
- Authentication utilities for API key management
- HTTP response models for consistent API responses

Usage:
    from dockrion_common import ValidationError, SUPPORTED_FRAMEWORKS
    from dockrion_common import validate_entrypoint, generate_api_key
    from dockrion_common import success_response, error_response
"""

# Error classes
from .errors import (
    DockrionError,
    ValidationError,
    AuthError,
    RateLimitError,
    NotFoundError,
    ConflictError,
    ServiceUnavailableError,
    DeploymentError,
    PolicyViolationError,
    MissingSecretError,
)

# Constants
from .constants import (
    # Version info
    DOCKRION_VERSION,
    SUPPORTED_DOCKFILE_VERSIONS,
    API_VERSION,
    # Supported values
    SUPPORTED_FRAMEWORKS,
    SUPPORTED_AUTH_MODES,
    SUPPORTED_STREAMING,
    LOG_LEVELS,
    # Permissions
    PERMISSIONS,
    # Defaults
    DEFAULT_CONTROLLER_PORT,
    DEFAULT_AUTH_PORT,
    DEFAULT_BUILDER_PORT,
    DEFAULT_RUNTIME_PORT,
    DEFAULT_DASHBOARD_BFF_PORT,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_BUILD_TIMEOUT,
    DEFAULT_INVOCATION_TIMEOUT,
    DEFAULT_RATE_LIMIT,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_CORS_METHODS,
    # Environment variables
    ENV_LANGFUSE_PUBLIC,
    ENV_LANGFUSE_SECRET,
    ENV_API_KEY,
    ENV_CONTROLLER_URL,
    ENV_AUTH_URL,
    ENV_BUILDER_URL,
    # Service names
    SERVICE_CONTROLLER,
    SERVICE_AUTH,
    SERVICE_BUILDER,
    SERVICE_RUNTIME,
    SERVICE_DASHBOARD_BFF,
    # Patterns
    AGENT_NAME_PATTERN,
    ENTRYPOINT_PATTERN,
    RATE_LIMIT_PATTERN,
    # HTTP status codes
    HTTP_OK,
    HTTP_CREATED,
    HTTP_ACCEPTED,
    HTTP_NO_CONTENT,
    HTTP_BAD_REQUEST,
    HTTP_UNAUTHORIZED,
    HTTP_FORBIDDEN,
    HTTP_NOT_FOUND,
    HTTP_CONFLICT,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE,
)

# Validation utilities
from .validation import (
    validate_entrypoint,
    validate_handler,
    validate_agent_name,
    parse_rate_limit,
    validate_url,
    sanitize_input,
    validate_port,
    validate_version,
)

# Auth utilities
from .auth_utils import (
    generate_api_key,
    hash_api_key,
    validate_api_key,
    extract_bearer_token,
    check_permission,
    check_any_permission,
    check_all_permissions,
    verify_api_key_format,
)

# HTTP models
from .http_models import (
    ErrorResponse,
    PaginatedResponse,
    HealthResponse,
    InvokeResponse,
    ReadyResponse,
    SchemaResponse,
    InfoResponse,
    error_response,
    paginated_response,
    health_response,
    invoke_response,
    ready_response,
    schema_response,
    info_response,
)

# Logger
from .logger import (
    DockrionLogger,
    get_logger,
    configure_logging,
    set_request_id,
    get_request_id,
    clear_request_id,
)

# Path utilities
from .path_utils import (
    resolve_module_path,
    add_to_python_path,
    setup_module_path,
)

# Environment utilities
from .env_utils import (
    load_env_files,
    resolve_secrets,
    validate_secrets,
    inject_env,
    get_env_summary,
)

__version__ = "0.1.0"

__all__ = [
    # Errors
    "DockrionError",
    "ValidationError",
    "AuthError",
    "RateLimitError",
    "NotFoundError",
    "ConflictError",
    "ServiceUnavailableError",
    "DeploymentError",
    "PolicyViolationError",
    "MissingSecretError",
    # Version info
    "DOCKRION_VERSION",
    "SUPPORTED_DOCKFILE_VERSIONS",
    "API_VERSION",
    # Supported values
    "SUPPORTED_FRAMEWORKS",
    "SUPPORTED_AUTH_MODES",
    "SUPPORTED_STREAMING",
    "LOG_LEVELS",
    # Permissions
    "PERMISSIONS",
    # Defaults
    "DEFAULT_CONTROLLER_PORT",
    "DEFAULT_AUTH_PORT",
    "DEFAULT_BUILDER_PORT",
    "DEFAULT_RUNTIME_PORT",
    "DEFAULT_DASHBOARD_BFF_PORT",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_REQUEST_TIMEOUT",
    "DEFAULT_BUILD_TIMEOUT",
    "DEFAULT_INVOCATION_TIMEOUT",
    "DEFAULT_RATE_LIMIT",
    "DEFAULT_CORS_ORIGINS",
    "DEFAULT_CORS_METHODS",
    # Environment variables
    "ENV_LANGFUSE_PUBLIC",
    "ENV_LANGFUSE_SECRET",
    "ENV_API_KEY",
    "ENV_CONTROLLER_URL",
    "ENV_AUTH_URL",
    "ENV_BUILDER_URL",
    # Service names
    "SERVICE_CONTROLLER",
    "SERVICE_AUTH",
    "SERVICE_BUILDER",
    "SERVICE_RUNTIME",
    "SERVICE_DASHBOARD_BFF",
    # Patterns
    "AGENT_NAME_PATTERN",
    "ENTRYPOINT_PATTERN",
    "RATE_LIMIT_PATTERN",
    # HTTP status codes
    "HTTP_OK",
    "HTTP_CREATED",
    "HTTP_ACCEPTED",
    "HTTP_NO_CONTENT",
    "HTTP_BAD_REQUEST",
    "HTTP_UNAUTHORIZED",
    "HTTP_FORBIDDEN",
    "HTTP_NOT_FOUND",
    "HTTP_CONFLICT",
    "HTTP_TOO_MANY_REQUESTS",
    "HTTP_INTERNAL_ERROR",
    "HTTP_SERVICE_UNAVAILABLE",
    # Validation
    "validate_entrypoint",
    "validate_handler",
    "validate_agent_name",
    "parse_rate_limit",
    "validate_url",
    "sanitize_input",
    "validate_port",
    "validate_version",
    # Auth
    "generate_api_key",
    "hash_api_key",
    "validate_api_key",
    "extract_bearer_token",
    "check_permission",
    "check_any_permission",
    "check_all_permissions",
    "verify_api_key_format",
    # HTTP Models
    "ErrorResponse",
    "PaginatedResponse",
    "HealthResponse",
    "InvokeResponse",
    "ReadyResponse",
    "SchemaResponse",
    "InfoResponse",
    "error_response",
    "paginated_response",
    "health_response",
    "invoke_response",
    "ready_response",
    "schema_response",
    "info_response",
    # Logger
    "DockrionLogger",
    "get_logger",
    "configure_logging",
    "set_request_id",
    "get_request_id",
    "clear_request_id",
    # Path utilities
    "resolve_module_path",
    "add_to_python_path",
    "setup_module_path",
    # Environment utilities
    "load_env_files",
    "resolve_secrets",
    "validate_secrets",
    "inject_env",
    "get_env_summary",
]
