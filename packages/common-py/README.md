# AgentDock Common Package

Shared utilities and primitives used across all AgentDock packages and services.

## Installation

```bash
pip install -e packages/common-py
```

## Overview

The `agentdock-common` package provides the foundation layer for AgentDock, offering:

- **Exception Classes**: Consistent error handling across all packages
- **Constants**: Single source of truth for supported values and defaults
- **Validation Utilities**: Reusable input validation functions
- **Authentication Utilities**: API key management and permission checking
- **HTTP Models**: Standard response formats for APIs
- **Application Logger**: Structured logging with JSON output and correlation IDs

## Usage

### Error Handling

```python
from agentdock_common import ValidationError, AuthError

# Raise validation errors
if not valid:
    raise ValidationError("Invalid entrypoint format")

# Catch AgentDock errors
try:
    validate_agent_name("My-Agent")
except ValidationError as e:
    print(f"Error: {e.message}, Code: {e.code}")
```

### Constants

```python
from agentdock_common import SUPPORTED_FRAMEWORKS, PERMISSIONS

# Check supported values
if framework not in SUPPORTED_FRAMEWORKS:
    raise ValidationError(f"Unsupported framework: {framework}")

# Use default values
from agentdock_common import DEFAULT_PORT, DEFAULT_HOST
server.run(host=DEFAULT_HOST, port=DEFAULT_PORT)
```

### Validation

```python
from agentdock_common import validate_entrypoint, validate_agent_name, parse_rate_limit

# Validate entrypoint
module, func = validate_entrypoint("app.main:build_graph")
# Returns: ("app.main", "build_graph")

# Validate agent name
validate_agent_name("invoice-copilot")  # Success
validate_agent_name("Invalid_Name")     # Raises ValidationError

# Parse rate limits
count, seconds = parse_rate_limit("1000/m")
# Returns: (1000, 60)
```

### Authentication

```python
from agentdock_common import generate_api_key, validate_api_key, check_permission

# Generate API keys
new_key = generate_api_key()  # Returns: "agd_..."

# Validate API keys
validate_api_key(
    header_value=request.headers.get("X-API-Key"),
    expected="agd_abc123..."
)  # Raises AuthError if invalid

# Check permissions
user_permissions = ["deploy", "invoke"]
if check_permission(user_permissions, "deploy"):
    # User has deploy permission
    pass
```

### HTTP Responses

```python
from agentdock_common import success_response, error_response, ValidationError

# Success response
return success_response({"id": "123", "status": "running"})
# Returns: {"success": True, "data": {"id": "123", "status": "running"}}

# Error response
try:
    validate_agent_name("Invalid")
except ValidationError as e:
    return error_response(e)
# Returns: {"success": False, "error": "...", "code": "VALIDATION_ERROR"}

# Paginated response
from agentdock_common import paginated_response

return paginated_response(
    items=[{"id": "1"}, {"id": "2"}],
    total=100,
    page=1,
    page_size=10
)
```

### Application Logging

```python
from agentdock_common import get_logger, set_request_id

# Create logger for your service
logger = get_logger("controller")

# Simple logging
logger.info("Service started", port=5001, version="1.0.0")
logger.error("Database connection failed", error=str(e), host="localhost")
logger.debug("Processing item", item_id="123", count=5)

# Logging with request context
set_request_id("req-abc-123")  # Set correlation ID
logger.info("Received request")  # Automatically includes request_id

# Persistent context (great for request handlers)
request_logger = logger.with_context(request_id="req-abc-123", user_id="user-456")
request_logger.info("Processing request")  # Includes both IDs
request_logger.info("Request complete")    # Also includes both IDs

# Exception logging with stack trace
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed", operation="risky")

# Output (JSON for easy parsing by ELK, Loki, CloudWatch):
# {"timestamp": "2024-11-11T10:30:00Z", "level": "INFO", "service": "controller",
#  "request_id": "req-abc-123", "message": "Processing request", "user_id": "user-456"}
```

## API Reference

### Error Classes

| Class | Code | Use Case |
|-------|------|----------|
| `AgentDockError` | INTERNAL_ERROR | Base exception for all AgentDock errors |
| `ValidationError` | VALIDATION_ERROR | Invalid input or configuration |
| `AuthError` | AUTH_ERROR | Authentication/authorization failures |
| `RateLimitError` | RATE_LIMIT_EXCEEDED | Rate limit exceeded |
| `NotFoundError` | NOT_FOUND | Resource not found |
| `ConflictError` | CONFLICT | Resource conflict (e.g., duplicate) |
| `ServiceUnavailableError` | SERVICE_UNAVAILABLE | Service temporarily unavailable |
| `DeploymentError` | DEPLOYMENT_ERROR | Deployment operation failures |
| `PolicyViolationError` | POLICY_VIOLATION | Policy rule violations |

### Constants

#### Version Info
- `AGENTDOCK_VERSION`: Platform version
- `SUPPORTED_DOCKFILE_VERSIONS`: Supported Dockfile versions
- `API_VERSION`: API version

#### Supported Values
- `SUPPORTED_FRAMEWORKS`: `["langgraph", "langchain"]`
- `SUPPORTED_PROVIDERS`: `["openai", "azure", "anthropic", "google", "ollama", "custom"]`
- `SUPPORTED_AUTH_MODES`: `["jwt", "api_key", "oauth2"]`
- `SUPPORTED_STREAMING`: `["sse", "websocket", "none"]`
- `LOG_LEVELS`: `["debug", "info", "warn", "error"]`

#### Permissions
- `PERMISSIONS`: List of available permissions

#### Defaults
- `DEFAULT_PORT`, `DEFAULT_HOST`: Service binding defaults
- `DEFAULT_REQUEST_TIMEOUT`: 30 seconds
- `DEFAULT_BUILD_TIMEOUT`: 600 seconds (10 minutes)
- `DEFAULT_RATE_LIMIT`: "100/m"

#### Patterns
- `AGENT_NAME_PATTERN`: Regex for valid agent names
- `ENTRYPOINT_PATTERN`: Regex for valid entrypoints
- `RATE_LIMIT_PATTERN`: Regex for rate limit format

### Validation Functions

| Function | Description | Example |
|----------|-------------|---------|
| `validate_entrypoint(str)` | Validate and parse entrypoint | `("app.main", "build")` |
| `validate_agent_name(str)` | Validate agent name format | Raises on invalid |
| `parse_rate_limit(str)` | Parse rate limit string | `(1000, 60)` |
| `validate_url(str)` | Validate URL format | Raises on invalid |
| `sanitize_input(str, max_length)` | Sanitize user input | Trimmed string |
| `validate_port(int)` | Validate port number | Raises if out of range |
| `validate_version(str)` | Validate semantic version | Raises on invalid |

### Auth Functions

| Function | Description | Returns |
|----------|-------------|---------|
| `generate_api_key(prefix)` | Generate secure API key | `"agd_..."` |
| `hash_api_key(key)` | Hash key for storage | Hex digest |
| `validate_api_key(header, expected)` | Validate API key | Raises on invalid |
| `extract_bearer_token(authorization)` | Extract Bearer token | Token or None |
| `check_permission(permissions, required)` | Check single permission | bool |
| `check_any_permission(permissions, required)` | Check any permission | bool |
| `check_all_permissions(permissions, required)` | Check all permissions | bool |
| `verify_api_key_format(key)` | Verify key format | bool |

### HTTP Models

| Function | Description | Returns |
|----------|-------------|---------|
| `success_response(data)` | Create success response | `{"success": True, "data": ...}` |
| `error_response(exception)` | Create error response | `{"success": False, "error": ..., "code": ...}` |
| `paginated_response(items, total, page, page_size)` | Create paginated response | Dict with pagination metadata |
| `health_response(service, version, status)` | Create health check response | Health check dict |

### Logger Functions

| Function | Description | Returns |
|----------|-------------|---------|
| `get_logger(service_name, log_level)` | Create a logger for a service | `AgentDockLogger` |
| `configure_logging(service_name, log_level)` | Configure and get logger | `AgentDockLogger` |
| `set_request_id(request_id)` | Set correlation ID for current context | None |
| `get_request_id()` | Get current correlation ID | `str` or `None` |
| `clear_request_id()` | Clear correlation ID | None |

#### AgentDockLogger Methods

| Method | Description | Example |
|--------|-------------|---------|
| `info(msg, **context)` | Log info message | `logger.info("Started", port=8080)` |
| `error(msg, **context)` | Log error message | `logger.error("Failed", error=str(e))` |
| `debug(msg, **context)` | Log debug message | `logger.debug("Details", data={})` |
| `warning(msg, **context)` | Log warning message | `logger.warning("High load", cpu=90)` |
| `critical(msg, **context)` | Log critical message | `logger.critical("Shutdown")` |
| `exception(msg, **context)` | Log exception with stack trace | `logger.exception("Error occurred")` |
| `with_context(**ctx)` | Create logger with persistent context | `logger.with_context(user_id="123")` |

## Dependencies

- `pydantic >= 2.5`: For HTTP response models

## Development

### Running Tests

```bash
cd packages/common-py
pytest tests/
```

### Type Checking

```bash
mypy agentdock_common/
```

## Design Principles

1. **Pure Utilities**: No I/O operations, no side effects
2. **Zero Internal Dependencies**: Foundation layer, doesn't depend on other AgentDock packages
3. **Minimal**: Only what's shared by 3+ packages
4. **Stable**: API designed for backward compatibility

## Future Extensions

When common package needs to be extended:

1. Add new modules only if used by 3+ packages
2. Use versioned constants for backward compatibility
3. Deprecate, don't remove (use `@deprecated` decorator)
4. Keep I/O operations in SDK, not common

## Support

For issues or questions:
- GitHub Issues: [AgentDock Repository](https://github.com/paritosh0707/AgentDock)
- Documentation: See `docs/COMMON_PACKAGE_IMPLEMENTATION_PLAN.md`

## License

See repository LICENSE file.

