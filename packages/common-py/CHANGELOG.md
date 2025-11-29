# Changelog - dockrion-common

All notable changes to the `dockrion-common` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2024-11-12

### Changed
- **Updated HTTP Models to Use Pydantic V2 ConfigDict**
  - Migrated all models from deprecated `class Config` to `model_config = ConfigDict()`
  - Updated models:
    - `APIResponse` - Standard success response model
    - `ErrorResponse` - Standard error response model
    - `PaginatedResponse` - Paginated list response model
    - `HealthResponse` - Health check response model
  - Removed all Pydantic deprecation warnings
  - Ensures compatibility with Pydantic V3 (future-proofing)

### Fixed
- Resolved 4 PydanticDeprecatedSince20 warnings in `http_models.py`

### Technical Details
The migration involved:
```python
# Before (deprecated)
class APIResponse(BaseModel):
    class Config:
        json_schema_extra = {...}

# After (modern Pydantic V2)
class APIResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={...}
    )
```

This change maintains 100% backward compatibility while following Pydantic V2 best practices.

## [0.1.0] - 2024-11-10

### Added
- Initial implementation of `dockrion-common` package
- **Error Classes** (`errors.py`):
  - `DockrionError` - Base exception class with `code` and `message` attributes
  - `ValidationError` - For input validation failures (code: `VALIDATION_ERROR`)
  - `AuthError` - For authentication/authorization failures (code: `AUTH_ERROR`)
  - `RateLimitError` - For rate limit violations (code: `RATE_LIMIT_EXCEEDED`)
  - `NotFoundError` - For missing resources (code: `NOT_FOUND`)
  - `ConflictError` - For resource conflicts (code: `CONFLICT`)
  - `ServiceUnavailableError` - For service unavailability (code: `SERVICE_UNAVAILABLE`)
  - `DeploymentError` - For deployment failures (code: `DEPLOYMENT_ERROR`)
  - `PolicyViolationError` - For policy violations (code: `POLICY_VIOLATION`)
  - All errors include `to_dict()` method for API serialization

- **Constants** (`constants.py`):
  - Version information: `dockrion_VERSION`, `SUPPORTED_DOCKFILE_VERSIONS`, `API_VERSION`
  - Supported values:
    - `SUPPORTED_FRAMEWORKS` - Agent frameworks (langgraph, langchain)
    - `SUPPORTED_PROVIDERS` - LLM providers (openai, azure, anthropic, google, ollama, custom)
    - `SUPPORTED_AUTH_MODES` - Auth modes (jwt, api_key, oauth2)
    - `SUPPORTED_STREAMING` - Streaming modes (sse, websocket, none)
    - `LOG_LEVELS` - Log levels (debug, info, warn, error)
    - `PERMISSIONS` - RBAC permissions (deploy, rollback, invoke, view_metrics, etc.)
  - Default values for ports, timeouts, rate limits, CORS
  - Environment variable names
  - Service names and identifiers
  - Validation patterns (regex):
    - `AGENT_NAME_PATTERN` - Agent name format
    - `ENTRYPOINT_PATTERN` - Entrypoint format (module:callable)
    - `RATE_LIMIT_PATTERN` - Rate limit format (e.g., 1000/m)
  - HTTP status codes for reference

- **Validation Functions** (`validation.py`):
  - `validate_entrypoint()` - Validates entrypoint format and prevents injection
  - `validate_agent_name()` - Validates agent name format
  - `validate_port()` - Validates port is in range 1-65535
  - `parse_rate_limit()` - Parses and validates rate limit strings

- **Authentication Utilities** (`auth_utils.py`):
  - `generate_api_key()` - Generates secure API keys with prefix
  - `hash_api_key()` - Hashes API keys using SHA-256
  - `validate_api_key()` - Validates API key format and content

- **HTTP Response Models** (`http_models.py`):
  - `APIResponse` - Standard success response with `success` and `data` fields
  - `ErrorResponse` - Standard error response with `error`, `code`, and `message` fields
  - `PaginatedResponse` - Paginated list response with pagination metadata
  - `HealthResponse` - Health check response for service monitoring
  - Helper functions:
    - `success_response()` - Creates success response dictionary
    - `error_response()` - Creates error response from exception
    - `paginated_response()` - Creates paginated response
    - `health_response()` - Creates health check response

- **Logging Utilities** (`logger.py`):
  - `get_logger()` - Returns configured logger instance
  - `configure_logging()` - Configures logging with log level and format
  - Context management for request IDs
  - Structured JSON logging support

- **Type Definitions** (`types.py`):
  - Common type aliases for type hints across packages

- Comprehensive test suite with 36 tests covering all modules
- Complete package documentation

### Dependencies
- `pydantic >= 2.0` - For data validation and HTTP models
- No internal Dockrion dependencies (foundation package)

### Design Principles
- **Single Source of Truth**: All shared constants and utilities in one place
- **Minimal Dependencies**: Only external dependencies, no internal package dependencies
- **Reusable**: Used by all Dockrion packages (schema, adapters, policy-engine, etc.)
- **Consistent Error Handling**: Unified error hierarchy for all services
- **Security-First**: Built-in validation and injection prevention

### Notes
- This package serves as the foundation for all other Dockrion packages
- Constants in this package are the canonical source for supported values
- Error classes in this package should be used by all Dockrion services
- No breaking changes should be introduced without major version bump

## [Unreleased]

### Planned for v0.2.0
- Add more validation utilities as needed by other packages
- Extend constants for Dockfile v1.1+ support (if needed)
- Add telemetry-related utilities (when telemetry package is developed)

