"""
dockrion Exception Classes

This module defines the exception hierarchy for all dockrion packages and services.
All custom exceptions inherit from DockrionError to enable consistent error handling.

Usage:
    from dockrion_common.errors import ValidationError, AuthError

    if not valid:
        raise ValidationError("Invalid entrypoint format")
"""


class DockrionError(Exception):
    """
    Base exception for all dockrion errors.

    All custom dockrion exceptions should inherit from this class to enable
    consistent error handling across packages and services.

    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
    """

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """
        Serialize error to dictionary for API responses.

        Returns:
            dict with error details including class name, code, and message
        """
        return {"error": self.__class__.__name__, "code": self.code, "message": self.message}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code='{self.code}', message='{self.message}')"


class ValidationError(DockrionError):
    """
    Raised when input validation fails.

    Use this for:
    - Invalid Dockfile configuration
    - Malformed entrypoint formats
    - Invalid agent names
    - Schema validation failures

    Example:
        if ":" not in entrypoint:
            raise ValidationError("Entrypoint must be in format 'module:callable'")
    """

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class AuthError(DockrionError):
    """
    Raised when authentication or authorization fails.

    Use this for:
    - Invalid API keys
    - Missing authentication tokens
    - Insufficient permissions
    - Failed JWT validation

    Example:
        if not valid_key:
            raise AuthError("Invalid API key")
    """

    def __init__(self, message: str):
        super().__init__(message, code="AUTH_ERROR")


class RateLimitError(AuthError):
    """
    Raised when rate limit is exceeded.

    Inherits from AuthError as rate limiting is part of access control.

    Use this for:
    - User exceeding request quota
    - Service-level rate limits

    Example:
        if request_count > limit:
            raise RateLimitError(f"Rate limit exceeded: {limit} requests per minute")
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "RATE_LIMIT_EXCEEDED"


class NotFoundError(DockrionError):
    """
    Raised when a requested resource is not found.

    Use this for:
    - Agent not found
    - Deployment not found
    - Configuration not found

    Example:
        if not deployment:
            raise NotFoundError(f"Deployment '{deployment_id}' not found")
    """

    def __init__(self, message: str):
        super().__init__(message, code="NOT_FOUND")


class ConflictError(DockrionError):
    """
    Raised when a resource conflict occurs.

    Use this for:
    - Duplicate agent names
    - Version conflicts
    - Concurrent modification issues

    Example:
        if agent_exists:
            raise ConflictError(f"Agent '{agent_name}' already exists")
    """

    def __init__(self, message: str):
        super().__init__(message, code="CONFLICT")


class ServiceUnavailableError(DockrionError):
    """
    Raised when a service is temporarily unavailable.

    Use this for:
    - Service downtime
    - Temporary network issues
    - Resource exhaustion

    Example:
        if not service_healthy:
            raise ServiceUnavailableError("Controller service is unavailable")
    """

    def __init__(self, message: str):
        super().__init__(message, code="SERVICE_UNAVAILABLE")


class DeploymentError(DockrionError):
    """
    Raised when deployment operations fail.

    Use this for:
    - Docker build failures
    - Image push failures
    - Deployment configuration errors

    Example:
        if build_failed:
            raise DeploymentError(f"Failed to build Docker image: {error}")
    """

    def __init__(self, message: str):
        super().__init__(message, code="DEPLOYMENT_ERROR")


class PolicyViolationError(DockrionError):
    """
    Raised when a policy is violated.

    Use this for:
    - Blocked tools
    - Content redaction triggers
    - Safety policy violations

    Example:
        if tool not in allowed_tools:
            raise PolicyViolationError(f"Tool '{tool}' is not allowed")
    """

    def __init__(self, message: str):
        super().__init__(message, code="POLICY_VIOLATION")


class MissingSecretError(ValidationError):
    """
    Raised when required secrets/environment variables are missing.

    This error provides a list of missing secret names for clear
    error messages and programmatic handling.

    Use this for:
    - Missing required environment variables before run
    - Missing secrets during build validation

    Example:
        missing = ["OPENAI_API_KEY", "MY_AGENT_KEY"]
        raise MissingSecretError(missing)
        # Message: "Missing required secrets: OPENAI_API_KEY, MY_AGENT_KEY"

    Attributes:
        missing: List of missing secret names
    """

    def __init__(self, missing: list):
        self.missing = missing
        message = f"Missing required secrets: {', '.join(missing)}"
        super().__init__(message)
        self.code = "MISSING_SECRET"

    def to_dict(self) -> dict:
        """Serialize error with missing secrets list."""
        result = super().to_dict()
        result["missing_secrets"] = self.missing
        return result


class BuildConflictError(DockrionError):
    """
    Raised when build include/exclude configuration has conflicts.

    Use this for:
    - Entrypoint module excluded from build
    - Auto-detected imports excluded from build
    - Critical configuration conflicts that would cause build failure

    Example:
        conflicts = ["utils (auto-detected import)", "models (auto-detected import)"]
        raise BuildConflictError(
            "Auto-detected imports are excluded from build",
            conflicts=conflicts
        )

    Attributes:
        conflicts: List of conflicting items
    """

    def __init__(self, message: str, conflicts: list | None = None):
        self.conflicts = conflicts if conflicts is not None else []
        super().__init__(message, code="BUILD_CONFLICT")

    def to_dict(self) -> dict:
        """Serialize error with conflicts list."""
        result = super().to_dict()
        result["conflicts"] = self.conflicts
        return result
