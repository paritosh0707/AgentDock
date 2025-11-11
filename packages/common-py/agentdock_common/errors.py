"""
AgentDock Exception Classes

This module defines the exception hierarchy for all AgentDock packages and services.
All custom exceptions inherit from AgentDockError to enable consistent error handling.

Usage:
    from agentdock_common.errors import ValidationError, AuthError
    
    if not valid:
        raise ValidationError("Invalid entrypoint format")
"""


class AgentDockError(Exception):
    """
    Base exception for all AgentDock errors.
    
    All custom AgentDock exceptions should inherit from this class to enable
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
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code='{self.code}', message='{self.message}')"


class ValidationError(AgentDockError):
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


class AuthError(AgentDockError):
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


class NotFoundError(AgentDockError):
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


class ConflictError(AgentDockError):
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


class ServiceUnavailableError(AgentDockError):
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


class DeploymentError(AgentDockError):
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


class PolicyViolationError(AgentDockError):
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
