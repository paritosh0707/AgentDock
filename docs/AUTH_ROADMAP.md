# Dockrion Authentication Roadmap

This document outlines the authentication and authorization capabilities of Dockrion, including what's currently implemented and what's planned for future phases.

## Overview

Dockrion provides enterprise-grade authentication for deployed AI agents. The auth system is designed to:

- **Scale from simple to enterprise**: Start with API keys, grow to SSO
- **Be declarative**: Configure auth in `Dockfile.yaml`, not code
- **Support multiple modes**: API keys, JWT, OAuth2 (future)
- **Enable RBAC**: Role-based access control with permissions
- **Integrate seamlessly**: Works with existing identity providers

---

## Current Implementation (Phase 1) ✅

### Implemented Features

#### 1. API Key Authentication

**Status:** ✅ Fully Implemented

**Capabilities:**
- Single key mode (one API key from environment variable)
- Multi-key mode (multiple keys with prefix pattern)
- Key metadata and role assignment
- Timing-safe key comparison (prevents timing attacks)
- Flexible header support (`X-API-Key` or `Authorization: Bearer`)

**Configuration:**
```yaml
# Simple single-key
auth:
  mode: api_key
  api_keys:
    env_var: MY_AGENT_KEY

# Multi-key for different clients
auth:
  mode: api_key
  api_keys:
    prefix: AGENT_KEY_  # Loads AGENT_KEY_PROD, AGENT_KEY_DEV, etc.
    header: X-API-Key
```

**Files:**
- `packages/runtime/dockrion_runtime/auth/api_key.py`

---

#### 2. JWT Authentication with JWKS

**Status:** ✅ Fully Implemented

**Capabilities:**
- JWKS (JSON Web Key Set) support for key rotation
- Static public key alternative
- RS256, ES256, and other algorithm support
- Standard claim validation (iss, aud, exp, nbf)
- Custom claim extraction to AuthContext
- Configurable clock skew tolerance

**Configuration:**
```yaml
auth:
  mode: jwt
  jwt:
    jwks_url: https://auth.company.com/.well-known/jwks.json
    issuer: https://auth.company.com/
    audience: my-agent-api
    algorithms: ["RS256"]
    leeway_seconds: 30
    claims:
      user_id: sub
      email: email
      roles: permissions
      tenant_id: org.tenant_id
```

**Files:**
- `packages/runtime/dockrion_runtime/auth/jwt_handler.py`

**Dependencies:**
- `PyJWT[crypto]>=2.8.0` (optional, installed via `pip install dockrion-runtime[jwt]`)

---

#### 3. Authentication Context (AuthContext)

**Status:** ✅ Fully Implemented

**Capabilities:**
- Unified identity context across all auth methods
- User ID, email, roles, permissions, scopes
- Tenant ID for multi-tenant scenarios
- Token expiry tracking
- Convenience methods (`has_role()`, `has_permission()`)
- Safe logging (PII-redacted)

**Usage in Handlers:**
```python
# Future: AuthContext will be injectable into handlers
async def process(payload: dict, auth: AuthContext) -> dict:
    print(f"Request from user: {auth.user_id}")
    if auth.has_role("admin"):
        # Admin-specific logic
        pass
    return result
```

**Files:**
- `packages/runtime/dockrion_runtime/auth/context.py`

---

#### 4. No-Auth Mode

**Status:** ✅ Fully Implemented

**Capabilities:**
- Passthrough mode for development
- Warning logged when disabled in production
- Returns anonymous context

**Configuration:**
```yaml
auth:
  mode: none  # No authentication required
```

---

#### 5. Role-Based Access Control (RBAC) Schema

**Status:** ✅ Schema Defined, ⚠️ Enforcement Pending

**Capabilities:**
- Define named roles with permissions
- Map roles to API keys or JWT claims
- Rate limits per role

**Configuration:**
```yaml
auth:
  mode: jwt
  roles:
    - name: admin
      permissions: [invoke, view_metrics, deploy, rollback]
    - name: operator
      permissions: [invoke, view_metrics]
    - name: viewer
      permissions: [view_metrics]
  rate_limits:
    admin: "1000/minute"
    operator: "100/minute"
    viewer: "10/minute"
```

**Files:**
- `packages/schema/dockrion_schema/dockfile_v1.py` (AuthConfig, RoleConfig)

---

#### 6. Auth Exceptions

**Status:** ✅ Fully Implemented

**Exception Hierarchy:**
```
AuthError (base)
├── AuthenticationError (401)
│   ├── MissingCredentialsError
│   ├── InvalidCredentialsError
│   ├── TokenExpiredError
│   └── TokenValidationError
├── AuthorizationError (403)
│   └── InsufficientPermissionsError
├── RateLimitExceededError (429)
└── ConfigurationError (500)
```

**Files:**
- `packages/runtime/dockrion_runtime/auth/exceptions.py`

---

#### 7. Extensible Handler Registry

**Status:** ✅ Fully Implemented

**Capabilities:**
- Register custom auth handlers
- Plugin architecture for enterprise integrations

**Usage:**
```python
from dockrion_runtime.auth import BaseAuthHandler, register_auth_handler

class SamlAuthHandler(BaseAuthHandler):
    async def authenticate(self, request):
        # Custom SAML logic
        return AuthContext.from_jwt(claims)

register_auth_handler("saml", SamlAuthHandler)
```

**Files:**
- `packages/runtime/dockrion_runtime/auth/factory.py`

---

## Planned Features (Phase 2) 🚧

### 1. OAuth2 Token Introspection

**Status:** 🚧 Schema Ready, Implementation Pending

**Planned Capabilities:**
- Validate opaque tokens via introspection endpoint
- Client credentials for service-to-service auth
- Scope-based authorization

**Schema (already defined):**
```yaml
auth:
  mode: oauth2
  oauth2:
    introspection_url: https://auth.company.com/oauth/introspect
    client_id_env: AGENT_CLIENT_ID
    client_secret_env: AGENT_CLIENT_SECRET
    required_scopes: [agent:invoke]
```

---

### 2. Rate Limiting

**Status:** 🚧 Schema Ready, Implementation Pending

**Planned Capabilities:**
- Token bucket algorithm
- Per-role rate limits
- Per-key/user rate limits
- Distributed rate limiting (Redis backend)
- Rate limit headers in responses

**Configuration:**
```yaml
auth:
  rate_limits:
    admin: "1000/minute"
    default: "100/minute"
  rate_limit_backend: redis  # or "memory"
```

---

### 3. RBAC Enforcement

**Status:** 🚧 Schema Ready, Enforcement Pending

**Planned Capabilities:**
- Automatic permission checking on endpoints
- Custom permission requirements per operation
- Audit logging for authorization decisions

---

### 4. AuthContext Injection into Handlers

**Status:** 🚧 Design Complete, Implementation Pending

**Planned Feature:**
```python
# Handler with auth context
def process_invoice(payload: dict, auth: AuthContext) -> dict:
    # Auth context automatically injected
    logger.info(f"Processing for user {auth.user_id}")
    return result
```

---

## Future Features (Phase 3) 📋

### 1. mTLS (Mutual TLS)

**Planned Capabilities:**
- Client certificate authentication
- Certificate validation against CA
- Integration with service meshes

### 2. Secrets Manager Integration

**Planned Capabilities:**
- AWS Secrets Manager for API keys
- HashiCorp Vault integration
- Azure Key Vault support
- GCP Secret Manager support

### 3. Key Management CLI

**Planned Commands:**
```bash
dockrion keys generate --prefix sk-prod
dockrion keys rotate --key-id prod --days 30
dockrion keys revoke --key-id old-key
dockrion keys list
```

### 4. Audit Logging

**Planned Capabilities:**
- Structured auth event logs
- Integration with SIEM systems
- Compliance-ready audit trails

### 5. API Gateway Integration

**Planned Capabilities:**
- AWS API Gateway authorizer
- Kong plugin
- Nginx auth module
- Istio integration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Dockfile.yaml                               │
│  auth:                                                              │
│    mode: jwt                                                        │
│    jwt: { jwks_url: ... }                                          │
│    roles: [...]                                                     │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Runtime Auth Module                            │
│  ┌─────────────┐                                                    │
│  │   Factory   │ create_auth_handler(config)                       │
│  └──────┬──────┘                                                    │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Handler Registry                          │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │   │
│  │  │ NoAuth  │  │ APIKey  │  │   JWT   │  │ OAuth2  │        │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     AuthContext                              │   │
│  │  • user_id, email, roles, permissions, scopes               │   │
│  │  • Available to handlers and middleware                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
packages/runtime/dockrion_runtime/auth/
├── __init__.py         # Package exports
├── base.py             # BaseAuthHandler, AuthConfig, NoAuthHandler
├── context.py          # AuthContext, AuthMethod
├── exceptions.py       # Auth exception hierarchy
├── api_key.py          # ApiKeyAuthHandler
├── jwt_handler.py      # JWTAuthHandler (requires PyJWT)
└── factory.py          # create_auth_handler(), registry
```

---

## Dependencies

| Feature | Required Packages | Install Command |
|---------|-------------------|-----------------|
| API Key | (none, built-in) | - |
| JWT | PyJWT, cryptography | `pip install dockrion-runtime[jwt]` |
| OAuth2 | httpx (future) | `pip install dockrion-runtime[oauth2]` |
| All | All auth features | `pip install dockrion-runtime[all]` |

---

## Migration Guide

### From v0.x (Basic Auth)

The old `AuthHandler` class has been replaced with a modular system:

**Before:**
```python
from dockrion_runtime.auth import AuthHandler, create_auth_handler

handler = create_auth_handler(config)
result = await handler.verify(request)  # Returns Optional[str]
```

**After:**
```python
from dockrion_runtime.auth import create_auth_handler, AuthContext

handler = create_auth_handler(config)
context = await handler.authenticate(request)  # Returns AuthContext
print(context.user_id, context.roles)
```

---

## Contributing

To add a new auth handler:

1. Create a new file in `packages/runtime/dockrion_runtime/auth/`
2. Extend `BaseAuthHandler`
3. Implement `authenticate(request) -> AuthContext`
4. Register in `factory.py` or use `register_auth_handler()`

Example:
```python
from .base import BaseAuthHandler, AuthConfig
from .context import AuthContext

class MyCustomHandler(BaseAuthHandler):
    async def authenticate(self, request):
        # Your logic here
        return AuthContext.from_api_key("key-id")
```

---

## Changelog

### v0.2.0 (Current)
- ✅ Modular auth architecture
- ✅ Enhanced API key handler (multi-key support)
- ✅ JWT handler with JWKS
- ✅ Unified AuthContext
- ✅ Typed exceptions
- ✅ Extensible handler registry

### v0.1.0
- Basic API key authentication
- Single key from environment variable

---

*Last updated: December 2024*

