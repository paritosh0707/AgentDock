"""
dockrion Common Package

Shared utilities and primitives used across all dockrion packages and services.

This package provides:
- Exception classes for consistent error handling
- Constants for supported values and defaults (namespaced)
- Validation utilities for input checking
- Authentication utilities for API key management
- HTTP response models for consistent API responses

Usage:
    from dockrion_common import ValidationError, SupportedValues
    from dockrion_common import validate_entrypoint, generate_api_key
    from dockrion_common import error_response, health_response
    
    # Namespaced constants (recommended)
    from dockrion_common import RuntimeDefaults, Timeouts, Patterns
    
    port = RuntimeDefaults.PORT
    timeout = Timeouts.INVOCATION
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

# Constants - Namespaced classes (recommended)
from .constants import (
    # Namespaced classes
    VersionInfo,
    SupportedValues,
    RuntimeDefaults,
    ServicePorts,
    Timeouts,
    ServiceNames,
    EnvVars,
    Patterns,
    HttpStatus,
    # Convenience aliases (lists from SupportedValues)
    DOCKRION_VERSION,
    SUPPORTED_DOCKFILE_VERSIONS,
    API_VERSION,
    SUPPORTED_FRAMEWORKS,
    SUPPORTED_AUTH_MODES,
    SUPPORTED_STREAMING,
    LOG_LEVELS,
    PERMISSIONS,
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
    # Namespaced constants (recommended)
    "VersionInfo",
    "SupportedValues",
    "RuntimeDefaults",
    "ServicePorts",
    "Timeouts",
    "ServiceNames",
    "EnvVars",
    "Patterns",
    "HttpStatus",
    # Convenience aliases
    "DOCKRION_VERSION",
    "SUPPORTED_DOCKFILE_VERSIONS",
    "API_VERSION",
    "SUPPORTED_FRAMEWORKS",
    "SUPPORTED_AUTH_MODES",
    "SUPPORTED_STREAMING",
    "LOG_LEVELS",
    "PERMISSIONS",
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
