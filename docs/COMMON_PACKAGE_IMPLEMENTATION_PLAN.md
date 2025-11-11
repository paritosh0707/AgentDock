# Common Package Implementation Plan

**Package:** `packages/common-py/agentdock_common`  
**Version:** 1.0  
**Status:** Implementation Plan  
**Last Updated:** November 11, 2024

---

## Executive Summary

The `common` package is the **foundation layer** of AgentDock, providing shared utilities and primitives used across all packages and services. This document outlines what will be built, how it will be implemented, and how it scales for future versions.

**Key Principles:**
- ✅ Minimal for V1 (only what's truly needed)
- ✅ Pure utilities (no I/O, no side effects)
- ✅ Zero internal dependencies (foundation layer)
- ✅ Scalable design (easy to extend without breaking changes)

---

## Table of Contents

1. [What Goes in Common Package](#what-goes-in-common-package)
2. [What Does NOT Go in Common](#what-does-not-go-in-common)
3. [Package Structure](#package-structure)
4. [Implementation Phases](#implementation-phases)
5. [Detailed Module Specifications](#detailed-module-specifications)
6. [Testing Strategy](#testing-strategy)
7. [Scalability Considerations](#scalability-considerations)
8. [Migration Path for Future Versions](#migration-path-for-future-versions)

---

## What Goes in Common Package

### ✅ V1 Core Modules (Must Have)

| Module | Purpose | Used By | Priority |
|--------|---------|---------|----------|
| **errors.py** | Exception classes | All packages (7+) | P0 |
| **constants.py** | Shared constants | Schema, SDK, CLI, Services (6+) | P0 |
| **validation.py** | Input validation utilities | Schema, SDK, CLI, Services (4+) | P0 |
| **auth_utils.py** | Authentication utilities | Auth, Runtime, Controller, Dashboard (4+) | P0 |
| **http_models.py** | API response models | All services (5+) | P0 |

**Total V1:** 5 modules, ~300 lines of code

### 🔶 V1.1+ Optional Modules (Future)

| Module | Purpose | When to Add |
|--------|---------|-------------|
| **rate_limiter.py** | Rate limiting utilities | When 3+ services need it |
| **crypto_utils.py** | Advanced crypto (beyond auth) | When encryption needed |
| **datetime_utils.py** | Date/time helpers | When 3+ packages need it |
| **retry.py** | Retry decorators | When services communicate |

---

## What Does NOT Go in Common

| Concern | Belongs In | Why |
|---------|-----------|-----|
| **File I/O** | SDK | I/O is orchestration, not utility |
| **YAML parsing** | SDK | Context-specific, not pure utility |
| **Logging** | Telemetry (agent) or Python logging (services) | Different purposes |
| **Schema definitions** | Schema package | Domain-specific |
| **Agent adapters** | Adapters package | Framework-specific |
| **Policy logic** | Policy-engine package | Domain-specific |
| **Business logic** | Services/SDK | Not a utility |

**Golden Rule:** If it's used by <3 packages, it doesn't belong in common.

---

## Package Structure

```
packages/common-py/
├── agentdock_common/
│   ├── __init__.py              # Public API exports
│   ├── errors.py                # Exception classes
│   ├── constants.py             # Shared constants
│   ├── validation.py            # Validation utilities
│   ├── auth_utils.py            # Authentication utilities
│   └── http_models.py           # HTTP response models
│
├── tests/
│   ├── __init__.py
│   ├── test_errors.py
│   ├── test_constants.py
│   ├── test_validation.py
│   ├── test_auth_utils.py
│   └── test_http_models.py
│
├── pyproject.toml               # Package configuration
├── README.md                    # Usage documentation
└── CHANGELOG.md                 # Version history
```

---

## Implementation Phases

### Phase 1: Foundation (Days 1-2) - P0

**Goal:** Establish core error classes and constants

**Deliverables:**
- ✅ `errors.py` - Complete exception hierarchy
- ✅ `constants.py` - All shared constants
- ✅ Basic tests for both modules
- ✅ `__init__.py` exports

**Dependencies:** None (pure Python)

**Success Criteria:**
- All error classes have proper inheritance
- Constants match schema definitions
- 100% test coverage for errors and constants

---

### Phase 2: Validation Utilities (Day 3) - P0

**Goal:** Input validation functions used across packages

**Deliverables:**
- ✅ `validation.py` - Entrypoint, agent name, rate limit parsing
- ✅ Integration with constants
- ✅ Comprehensive tests

**Dependencies:** `errors.py`, `constants.py`

**Success Criteria:**
- All validation functions tested
- Clear error messages
- Handles edge cases

---

### Phase 3: Auth Utilities (Day 4) - P0

**Goal:** Authentication helpers for API keys

**Deliverables:**
- ✅ `auth_utils.py` - Key generation, validation, hashing
- ✅ Security best practices
- ✅ Tests including security scenarios

**Dependencies:** `errors.py`

**Success Criteria:**
- Secure key generation
- Proper validation logic
- No security vulnerabilities

---

### Phase 4: HTTP Models (Day 5) - P0

**Goal:** Standard API response formats

**Deliverables:**
- ✅ `http_models.py` - Response models and helpers
- ✅ Error response formatting
- ✅ Tests for all models

**Dependencies:** `errors.py`, `pydantic`

**Success Criteria:**
- Consistent response format
- Proper error serialization
- Easy to use helpers

---

### Phase 5: Integration & Documentation (Day 6) - P0

**Goal:** Package is ready for use by other teams

**Deliverables:**
- ✅ Complete README with examples
- ✅ Integration tests with other packages
- ✅ CHANGELOG
- ✅ Type hints and docstrings

**Success Criteria:**
- Other teams can use it without confusion
- All examples work
- Documentation is clear

---

### Phase 6: Polish & Review (Day 7) - P0

**Goal:** Production-ready package

**Deliverables:**
- ✅ Code review
- ✅ Performance validation
- ✅ Security audit
- ✅ Final documentation pass

**Total V1 Timeline:** 7 days

---

## Detailed Module Specifications

### 1. errors.py

**Purpose:** Standardized exception classes for all AgentDock packages

**Design:**
```python
# Base hierarchy
AgentDockError (base)
├── ValidationError
├── AuthError
│   └── RateLimitError
├── NotFoundError
├── ConflictError
└── ServiceUnavailableError
```

**Implementation:**
```python
class AgentDockError(Exception):
    """Base exception for all AgentDock errors"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Serialize to dict for API responses"""
        return {"error": self.__class__.__name__, "code": self.code, "message": self.message}

class ValidationError(AgentDockError):
    """Invalid input or configuration"""
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")

class AuthError(AgentDockError):
    """Authentication/authorization failed"""
    def __init__(self, message: str):
        super().__init__(message, code="AUTH_ERROR")

class RateLimitError(AuthError):
    """Rate limit exceeded"""
    def __init__(self, message: str):
        super().__init__(message)
        self.code = "RATE_LIMIT_EXCEEDED"

class NotFoundError(AgentDockError):
    """Resource not found"""
    def __init__(self, message: str):
        super().__init__(message, code="NOT_FOUND")

class ConflictError(AgentDockError):
    """Resource conflict (e.g., duplicate)"""
    def __init__(self, message: str):
        super().__init__(message, code="CONFLICT")

class ServiceUnavailableError(AgentDockError):
    """Service temporarily unavailable"""
    def __init__(self, message: str):
        super().__init__(message, code="SERVICE_UNAVAILABLE")
```

**Usage:**
```python
from agentdock_common.errors import ValidationError, AuthError

if not valid:
    raise ValidationError("Invalid entrypoint format")
```

**Scalability:**
- Easy to add new error types
- Error codes are strings (extensible)
- `to_dict()` enables consistent API responses

---

### 2. constants.py

**Purpose:** Single source of truth for supported values and defaults

**Design:**
```python
# Version info
AGENTDOCK_VERSION = "1.0"
SUPPORTED_DOCKFILE_VERSIONS = ["1.0"]

# Supported values (must match schema)
SUPPORTED_FRAMEWORKS = ["langgraph", "langchain"]
SUPPORTED_PROVIDERS = ["openai", "azure", "anthropic", "google", "ollama", "custom"]
SUPPORTED_AUTH_MODES = ["jwt", "api_key", "oauth2"]
SUPPORTED_STREAMING = ["sse", "websocket", "none"]
LOG_LEVELS = ["debug", "info", "warn", "error"]

# Default ports for services (local development)
DEFAULT_CONTROLLER_PORT = 5001
DEFAULT_AUTH_PORT = 5002
DEFAULT_BUILDER_PORT = 5003
DEFAULT_RUNTIME_PORT = 8080
DEFAULT_DASHBOARD_BFF_PORT = 4000

# API versions
API_VERSION = "v1"

# Timeouts (seconds)
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_BUILD_TIMEOUT = 600  # 10 minutes

# Permissions (used in auth and controller)
PERMISSIONS = [
    "deploy",
    "rollback",
    "invoke",
    "view_metrics",
    "key_manage",
    "read_logs",
    "read_docs",
]

# Rate limit defaults
DEFAULT_RATE_LIMIT = "100/m"
```

**Usage:**
```python
from agentdock_common.constants import SUPPORTED_FRAMEWORKS, PERMISSIONS

if framework not in SUPPORTED_FRAMEWORKS:
    raise ValidationError(f"Unsupported framework: {framework}")
```

**Scalability:**
- Easy to add new constants
- Versioned constants (e.g., `SUPPORTED_FRAMEWORKS_V1`, `SUPPORTED_FRAMEWORKS_V2`)
- Can be extended without breaking changes

---

### 3. validation.py

**Purpose:** Reusable validation functions

**Functions:**
```python
def validate_entrypoint(entrypoint: str) -> tuple[str, str]:
    """
    Validate and parse entrypoint format: 'module.path:callable'
    Returns: (module_path, callable_name)
    Raises: ValidationError if invalid
    """
    pass

def validate_agent_name(name: str) -> None:
    """
    Validate agent name (lowercase, alphanumeric, hyphens only)
    Raises: ValidationError if invalid
    """
    pass

def parse_rate_limit(limit_str: str) -> tuple[int, int]:
    """
    Parse rate limit string like '1000/m' to (count, seconds)
    Examples:
        '100/s' -> (100, 1)
        '1000/m' -> (1000, 60)
        '5000/h' -> (5000, 3600)
    Raises: ValidationError if invalid format
    """
    pass

def validate_url(url: str) -> None:
    """
    Validate URL format
    Raises: ValidationError if invalid
    """
    pass

def sanitize_input(text: str, max_length: int | None = None) -> str:
    """
    Sanitize user input (trim, length check)
    Returns: Sanitized string
    """
    pass
```

**Usage:**
```python
from agentdock_common.validation import validate_entrypoint, parse_rate_limit

module, func = validate_entrypoint("app.main:build_graph")
count, seconds = parse_rate_limit("1000/m")
```

**Scalability:**
- Functions are pure (easy to test)
- Can add new validators without breaking existing ones
- Can be extended with custom validators

---

### 4. auth_utils.py

**Purpose:** Authentication and authorization utilities

**Functions:**
```python
def generate_api_key(prefix: str = "agd") -> str:
    """
    Generate a secure API key
    Format: {prefix}_{random_32_chars}
    Returns: e.g., "agd_8f7g9h2j3k4l5m6n7o8p9q0r1s2t3u4v5w6x7y"
    """
    pass

def hash_api_key(key: str) -> str:
    """
    Hash API key for storage (one-way, SHA-256)
    Returns: Hex digest
    """
    pass

def validate_api_key(header_value: str | None, expected: str | None) -> None:
    """
    Validate API key from request header
    Raises: AuthError if invalid
    """
    pass

def extract_bearer_token(authorization: str | None) -> str | None:
    """
    Extract token from 'Bearer <token>' header
    Returns: Token string or None
    """
    pass

def check_permission(user_permissions: list[str], required: str) -> bool:
    """
    Check if user has required permission
    Returns: True if user has permission
    """
    pass
```

**Usage:**
```python
from agentdock_common.auth_utils import generate_api_key, validate_api_key

new_key = generate_api_key()
validate_api_key(request.headers.get("X-API-Key"), expected_key)
```

**Scalability:**
- Can add JWT utilities later (V2)
- Can add OAuth2 helpers later (V2)
- Crypto functions can be extended

---

### 5. http_models.py

**Purpose:** Standard API response formats

**Models:**
```python
class APIResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    data: Any

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    code: str

class PaginatedResponse(BaseModel):
    """Paginated list response"""
    success: bool = True
    items: List[Any]
    total: int
    page: int
    page_size: int

# Helper functions
def success_response(data: Any) -> dict:
    """Create success response dict"""
    pass

def error_response(error: Exception) -> dict:
    """Create error response dict from exception"""
    pass
```

**Usage:**
```python
from agentdock_common.http_models import success_response, error_response

return success_response({"id": "123", "status": "running"})
return error_response(ValidationError("Invalid input"))
```

**Scalability:**
- Can add more response types (streaming, etc.)
- Models are Pydantic (extensible)
- Helpers can be extended

---

## Testing Strategy

### Test Coverage Goals

- **Unit Tests:** >95% coverage
- **Integration Tests:** All public APIs
- **Edge Cases:** All validation functions
- **Security Tests:** Auth utilities

### Test Structure

```python
# tests/test_validation.py
def test_validate_entrypoint_valid():
    """Test valid entrypoint formats"""
    assert validate_entrypoint("app.main:build") == ("app.main", "build")

def test_validate_entrypoint_invalid():
    """Test invalid entrypoint formats"""
    with pytest.raises(ValidationError):
        validate_entrypoint("missing_colon")

def test_parse_rate_limit():
    """Test rate limit parsing"""
    assert parse_rate_limit("1000/m") == (1000, 60)
    assert parse_rate_limit("60/s") == (60, 1)
```

### Testing Principles

1. **Pure Functions:** Easy to test (no mocking needed)
2. **Fast Tests:** All tests run in <1 second
3. **Clear Assertions:** Each test has one clear purpose
4. **Edge Cases:** Test boundaries, invalid inputs, None values

---

## Scalability Considerations

### 1. Version Compatibility

**Strategy:** Use versioned constants and functions

```python
# V1
SUPPORTED_FRAMEWORKS = ["langgraph", "langchain"]

# V2 (additive, doesn't break V1)
SUPPORTED_FRAMEWORKS_V2 = ["langgraph", "langchain", "autogen"]

# Or use a function
def get_supported_frameworks(version: str = "1.0") -> list[str]:
    if version == "1.0":
        return ["langgraph", "langchain"]
    elif version == "2.0":
        return ["langgraph", "langchain", "autogen"]
```

### 2. Extensibility

**Strategy:** Use protocols/interfaces for future implementations

```python
# V1: Simple function
def generate_api_key(prefix: str = "agd") -> str:
    pass

# V2: Can add interface
class APIKeyGenerator(Protocol):
    def generate(self, prefix: str) -> str: ...

# V1 function still works, V2 can use interface
```

### 3. Backward Compatibility

**Strategy:** Never remove, only deprecate

```python
# V1
def old_function():
    pass

# V2
@deprecated("Use new_function() instead")
def old_function():
    return new_function()
```

### 4. Performance

**Strategy:** Keep functions pure and fast

- No I/O in common (already enforced)
- No heavy computations
- Cache expensive operations if needed (V2+)

### 5. Dependency Management

**Strategy:** Minimal dependencies, optional extras

```toml
# pyproject.toml
[project]
dependencies = [
    "pydantic>=2.5",  # Only for http_models
]

[project.optional-dependencies]
crypto = [
    "cryptography>=41.0",  # Only if advanced crypto needed
]
```

---

## Migration Path for Future Versions

### V1 → V1.1 (Add Rate Limiting)

**When:** 3+ services need rate limiting utilities

**Changes:**
```python
# Add to common/rate_limiter.py
class RateLimiter:
    def parse_rate_limit(self, limit_str: str) -> tuple[int, int]:
        # Move from validation.py or add new implementation
        pass
    
    def check_limit(self, user_id: str, limit: tuple[int, int]) -> bool:
        pass
```

**Migration:**
- Keep `parse_rate_limit()` in `validation.py` (backward compatible)
- Add `RateLimiter` class for advanced usage
- Services can migrate gradually

### V1 → V2 (Add Caching Abstraction)

**When:** Services need Redis/memory caching

**Changes:**
```python
# Add to common/cache/interface.py
class CacheBackend(Protocol):
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: int | None) -> None: ...

# Add implementations
class InMemoryCache(CacheBackend): ...
class RedisCache(CacheBackend): ...
```

**Migration:**
- Services can opt-in to caching
- No breaking changes to existing code

### V1 → V2 (Add Service Discovery)

**When:** Services need to discover each other

**Changes:**
```python
# Add to common/service_discovery/client.py
class ServiceClient:
    def __init__(self, service_name: str, base_url: str | None = None):
        # Uses env vars or explicit URL
        pass
```

**Migration:**
- Services can use it or continue with env vars
- No breaking changes

---

## Success Metrics

### Technical Metrics

- ✅ **Zero internal dependencies:** Common doesn't import other AgentDock packages
- ✅ **>95% test coverage:** All functions tested
- ✅ **<100ms import time:** Fast to import
- ✅ **Type hints:** 100% type coverage (mypy strict)

### Usage Metrics

- ✅ **Used by 5+ packages:** SDK, CLI, Schema, Services
- ✅ **No duplication:** Validation logic not duplicated elsewhere
- ✅ **Clear API:** Developers know what to use

### Quality Metrics

- ✅ **No breaking changes:** V1 API stable
- ✅ **Clear documentation:** README with examples
- ✅ **Security:** Auth utilities follow best practices

---

## Dependencies

### Required (V1)

```toml
[project]
dependencies = [
    "pydantic>=2.5",  # For http_models.py
]
```

### Optional (Future)

```toml
[project.optional-dependencies]
crypto = [
    "cryptography>=41.0",  # For advanced crypto (V2+)
]
redis = [
    "redis>=5.0",  # For caching (V2+)
]
```

**Principle:** Keep dependencies minimal. Add only when absolutely necessary.

---

## Public API (__init__.py)

```python
# agentdock_common/__init__.py

# Errors
from .errors import (
    AgentDockError,
    ValidationError,
    AuthError,
    RateLimitError,
    NotFoundError,
    ConflictError,
    ServiceUnavailableError,
)

# Constants
from .constants import (
    AGENTDOCK_VERSION,
    SUPPORTED_FRAMEWORKS,
    SUPPORTED_PROVIDERS,
    SUPPORTED_AUTH_MODES,
    PERMISSIONS,
    DEFAULT_RATE_LIMIT,
)

# Validation
from .validation import (
    validate_entrypoint,
    validate_agent_name,
    parse_rate_limit,
    validate_url,
    sanitize_input,
)

# Auth
from .auth_utils import (
    generate_api_key,
    hash_api_key,
    validate_api_key,
    extract_bearer_token,
    check_permission,
)

# HTTP Models
from .http_models import (
    APIResponse,
    ErrorResponse,
    PaginatedResponse,
    success_response,
    error_response,
)

__version__ = "0.1.0"
__all__ = [
    # Errors
    "AgentDockError",
    "ValidationError",
    "AuthError",
    "RateLimitError",
    "NotFoundError",
    "ConflictError",
    "ServiceUnavailableError",
    # Constants
    "AGENTDOCK_VERSION",
    "SUPPORTED_FRAMEWORKS",
    "SUPPORTED_PROVIDERS",
    "SUPPORTED_AUTH_MODES",
    "PERMISSIONS",
    "DEFAULT_RATE_LIMIT",
    # Validation
    "validate_entrypoint",
    "validate_agent_name",
    "parse_rate_limit",
    "validate_url",
    "sanitize_input",
    # Auth
    "generate_api_key",
    "hash_api_key",
    "validate_api_key",
    "extract_bearer_token",
    "check_permission",
    # HTTP Models
    "APIResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "success_response",
    "error_response",
]
```

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create package structure
- [ ] Implement `errors.py` with all exception classes
- [ ] Implement `constants.py` with all constants
- [ ] Write tests for errors and constants
- [ ] Update `__init__.py` exports

### Phase 2: Validation
- [ ] Implement `validation.py` with all functions
- [ ] Write comprehensive tests
- [ ] Test edge cases and error handling
- [ ] Update `__init__.py` exports

### Phase 3: Auth
- [ ] Implement `auth_utils.py` with all functions
- [ ] Write security-focused tests
- [ ] Validate crypto best practices
- [ ] Update `__init__.py` exports

### Phase 4: HTTP Models
- [ ] Implement `http_models.py` with all models
- [ ] Write tests for serialization
- [ ] Test error response formatting
- [ ] Update `__init__.py` exports

### Phase 5: Integration
- [ ] Write README with examples
- [ ] Create integration tests
- [ ] Write CHANGELOG
- [ ] Add type hints and docstrings

### Phase 6: Polish
- [ ] Code review
- [ ] Performance validation
- [ ] Security audit
- [ ] Final documentation pass

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|------------|
| Phase 1: Foundation | 2 days | errors.py, constants.py |
| Phase 2: Validation | 1 day | validation.py |
| Phase 3: Auth | 1 day | auth_utils.py |
| Phase 4: HTTP Models | 1 day | http_models.py |
| Phase 5: Integration | 1 day | Documentation, tests |
| Phase 6: Polish | 1 day | Review, audit |
| **Total** | **7 days** | **Production-ready package** |

---

## Next Steps

1. **Review this plan** with the team
2. **Assign ownership** for each phase
3. **Set up development environment** (repo, CI/CD)
4. **Start Phase 1** (Foundation)
5. **Daily sync** to track progress

---

## Questions & Decisions Needed

1. **Error codes:** Use strings (current) or integers? → **Decision: Strings (more readable)**
2. **Rate limiting:** In-memory or Redis? → **Decision: V1 in-memory, V2 Redis**
3. **Caching:** Add in V1 or defer? → **Decision: Defer to V2**
4. **Service discovery:** Add in V1 or defer? → **Decision: Defer to V2**

---

## Conclusion

The common package is the **foundation** of AgentDock. By keeping it minimal, pure, and well-tested, we ensure:

- ✅ Fast development (other teams can start immediately)
- ✅ Consistent behavior (shared utilities prevent bugs)
- ✅ Easy maintenance (clear boundaries, minimal dependencies)
- ✅ Future scalability (extensible design)

**This plan provides a clear roadmap for building a production-ready common package in 7 days.**

