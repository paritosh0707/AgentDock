"""
Dockrion Runtime Authentication Module

Provides enterprise-grade authentication for deployed agents.

Supported authentication modes:
- **none**: No authentication (development/trusted networks)
- **api_key**: API key authentication (single or multi-key)
- **jwt**: JWT with JWKS support (enterprise SSO integration)
- **oauth2**: OAuth2 token introspection (future)

Quick Start:
    >>> from dockrion_runtime.auth import create_auth_handler, AuthContext

    >>> # From DockSpec config
    >>> handler = create_auth_handler(spec.auth.model_dump())

    >>> # In request handler
    >>> context = await handler.authenticate(request)
    >>> print(context.user_id)

Configuration Example (Dockfile.yaml):
    ```yaml
    auth:
      mode: jwt
      jwt:
        jwks_url: https://auth.company.com/.well-known/jwks.json
        issuer: https://auth.company.com/
        audience: my-agent-api
        claims:
          user_id: sub
          email: email
          roles: permissions
    ```

For custom authentication:
    >>> from dockrion_runtime.auth import (
    ...     BaseAuthHandler,
    ...     AuthConfig,
    ...     register_auth_handler
    ... )

    >>> class MyAuthHandler(BaseAuthHandler):
    ...     async def authenticate(self, request):
    ...         # Your logic here
    ...         return AuthContext.from_api_key("my-key")

    >>> register_auth_handler("my_auth", MyAuthHandler)
"""

# Core classes
# Handlers
from .api_key import ApiKeyAuthHandler, generate_api_key, hash_api_key
from .base import AuthConfig, BaseAuthHandler, NoAuthHandler
from .context import AuthContext, AuthMethod
from .exceptions import (
    AuthenticationError,
    AuthError,
    AuthorizationError,
    ConfigurationError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    MissingCredentialsError,
    RateLimitExceededError,
    TokenExpiredError,
    TokenValidationError,
)

# Factory
from .factory import (
    create_auth_handler,
    get_available_auth_modes,
    register_auth_handler,
)

# Conditional JWT import
try:
    from .jwt_handler import JWTAuthHandler

    _jwt_available = True
except ImportError:
    JWTAuthHandler = None  # type: ignore
    _jwt_available = False


def is_jwt_available() -> bool:
    """Check if JWT authentication is available."""
    return _jwt_available


__all__ = [
    # Context
    "AuthContext",
    "AuthMethod",
    # Base classes
    "BaseAuthHandler",
    "AuthConfig",
    "NoAuthHandler",
    # Handlers
    "ApiKeyAuthHandler",
    "JWTAuthHandler",
    # Factory
    "create_auth_handler",
    "get_available_auth_modes",
    "register_auth_handler",
    # Utilities
    "generate_api_key",
    "hash_api_key",
    "is_jwt_available",
    # Exceptions
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "MissingCredentialsError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenValidationError",
    "InsufficientPermissionsError",
    "RateLimitExceededError",
    "ConfigurationError",
]
