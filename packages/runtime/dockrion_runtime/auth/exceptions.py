"""
Authentication Exceptions for Dockrion Runtime

Provides typed exceptions for authentication and authorization errors.
These are converted to appropriate HTTP responses by the middleware.
"""

from typing import Any, Dict, Optional


class AuthError(Exception):
    """
    Base exception for all authentication/authorization errors.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code for clients
        status_code: HTTP status code to return
        details: Additional error context
    """

    def __init__(
        self,
        message: str,
        error_code: str = "AUTH_ERROR",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {"error": self.error_code, "message": self.message, "details": self.details}


class AuthenticationError(AuthError):
    """
    Raised when authentication fails (invalid or missing credentials).

    HTTP Status: 401 Unauthorized
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTHENTICATION_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, error_code=error_code, status_code=401, details=details)


class MissingCredentialsError(AuthenticationError):
    """Raised when required credentials are not provided."""

    def __init__(
        self,
        message: str = "Missing authentication credentials",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, error_code="MISSING_CREDENTIALS", details=details)


class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid authentication credentials",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, error_code="INVALID_CREDENTIALS", details=details)


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT or token has expired."""

    def __init__(
        self, message: str = "Token has expired", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, error_code="TOKEN_EXPIRED", details=details)


class TokenValidationError(AuthenticationError):
    """Raised when token validation fails (signature, claims, etc.)."""

    def __init__(
        self, message: str = "Token validation failed", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, error_code="TOKEN_INVALID", details=details)


class AuthorizationError(AuthError):
    """
    Raised when authorization fails (valid credentials but insufficient permissions).

    HTTP Status: 403 Forbidden
    """

    def __init__(
        self,
        message: str = "Permission denied",
        error_code: str = "AUTHORIZATION_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, error_code=error_code, status_code=403, details=details)


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions."""

    def __init__(
        self,
        required_permissions: list[str],
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if not message:
            message = f"Missing required permissions: {', '.join(required_permissions)}"

        super().__init__(
            message=message,
            error_code="INSUFFICIENT_PERMISSIONS",
            details={**(details or {}), "required_permissions": required_permissions},
        )


class RateLimitExceededError(AuthError):
    """
    Raised when rate limit is exceeded.

    HTTP Status: 429 Too Many Requests
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={**(details or {}), "retry_after": retry_after},
        )
        self.retry_after = retry_after


class ConfigurationError(AuthError):
    """
    Raised when auth is misconfigured (missing env vars, etc.).

    HTTP Status: 500 Internal Server Error
    """

    def __init__(
        self,
        message: str = "Authentication configuration error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message, error_code="AUTH_CONFIG_ERROR", status_code=500, details=details
        )
