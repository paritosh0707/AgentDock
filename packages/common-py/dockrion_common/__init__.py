"""
dockrion Common Package

Shared utilities and primitives used across all dockrion packages and services.

This package provides:
- Exception classes for consistent error handling
- Constants for supported values and defaults (namespaced)
- Validation utilities for input checking
- Authentication utilities for API key management
- Pydantic HTTP response models for FastAPI

Usage:
    from dockrion_common import ValidationError, SupportedValues
    from dockrion_common import validate_entrypoint, generate_api_key
    from dockrion_common import HealthResponse, InvokeResponse, ErrorResponse

    # Namespaced constants (recommended)
    from dockrion_common import RuntimeDefaults, Timeouts, Patterns

    port = RuntimeDefaults.PORT
    timeout = Timeouts.INVOCATION
"""

# Error classes
# Auth utilities
from .auth_utils import (
    check_all_permissions,
    check_any_permission,
    check_permission,
    extract_bearer_token,
    generate_api_key,
    hash_api_key,
    validate_api_key,
    verify_api_key_format,
)

# Constants - Namespaced classes (recommended)
from .constants import (
    API_VERSION,
    # Convenience aliases (lists from SupportedValues)
    DOCKRION_VERSION,
    LOG_LEVELS,
    PERMISSIONS,
    SUPPORTED_AUTH_MODES,
    SUPPORTED_DOCKFILE_VERSIONS,
    SUPPORTED_FRAMEWORKS,
    SUPPORTED_STREAMING,
    EnvVars,
    HttpStatus,
    Patterns,
    RuntimeDefaults,
    ServiceNames,
    ServicePorts,
    SupportedValues,
    Timeouts,
    # Namespaced classes
    VersionInfo,
)

# Environment utilities
from .env_utils import (
    get_env_summary,
    inject_env,
    load_env_files,
    resolve_secrets,
    validate_secrets,
)
from .errors import (
    AuthError,
    ConflictError,
    DeploymentError,
    DockrionError,
    MissingSecretError,
    NotFoundError,
    PolicyViolationError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)

# HTTP models (Pydantic response models for FastAPI)
from .http_models import (
    ErrorResponse,
    HealthResponse,
    InfoResponse,
    InvokeResponse,
    PaginatedResponse,
    ReadyResponse,
    SchemaResponse,
)

# Logger
from .logger import (
    DockrionLogger,
    clear_request_id,
    configure_logging,
    get_logger,
    get_request_id,
    set_request_id,
)

# Path utilities
from .path_utils import (
    add_to_python_path,
    resolve_module_path,
    setup_module_path,
)

# Validation utilities
from .validation import (
    parse_rate_limit,
    sanitize_input,
    validate_agent_name,
    validate_entrypoint,
    validate_handler,
    validate_port,
    validate_url,
    validate_version,
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
    # HTTP Models (Pydantic response models for FastAPI)
    "ErrorResponse",
    "PaginatedResponse",
    "HealthResponse",
    "InvokeResponse",
    "ReadyResponse",
    "SchemaResponse",
    "InfoResponse",
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
