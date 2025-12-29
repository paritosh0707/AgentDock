"""
Authentication Factory for Dockrion Runtime

Creates the appropriate auth handler based on configuration.
This is the main entry point for the auth module.
"""

from typing import Any, Dict, Optional, Type

from dockrion_common.logger import get_logger

from .api_key import ApiKeyAuthHandler
from .base import AuthConfig, BaseAuthHandler, NoAuthHandler

logger = get_logger(__name__)

# Registry of auth handlers by mode
_AUTH_HANDLERS: Dict[str, Type[BaseAuthHandler]] = {
    "none": NoAuthHandler,
    "api_key": ApiKeyAuthHandler,
    # jwt and oauth2 added conditionally below
}

# Try to register JWT handler
try:
    from .jwt_handler import JWTAuthHandler

    _AUTH_HANDLERS["jwt"] = JWTAuthHandler
except ImportError:
    logger.debug("JWT handler not available (PyJWT not installed)")


def create_auth_handler(
    auth_config: Optional[Dict[str, Any]] = None, *, mode_override: Optional[str] = None
) -> BaseAuthHandler:
    """
    Factory function to create the appropriate auth handler.

    This is the main entry point for authentication setup.
    Call this during app initialization with the auth section
    from DockSpec.

    Args:
        auth_config: The 'auth' section from DockSpec, as a dict
        mode_override: Override the mode from config (for testing)

    Returns:
        Configured BaseAuthHandler instance

    Raises:
        ValueError: If auth mode is not supported
        ImportError: If required dependencies are missing

    Example:
        >>> # From DockSpec
        >>> handler = create_auth_handler(spec.auth.model_dump())

        >>> # For testing
        >>> handler = create_auth_handler(mode_override="none")
    """
    # Handle no config case
    if not auth_config:
        logger.info("No auth config provided, using NoAuthHandler")
        return NoAuthHandler()

    # Build AuthConfig from dict
    config = AuthConfig.from_dict(auth_config)

    # Apply override if provided
    mode = mode_override or config.mode

    # Handle disabled auth
    if not config.enabled or mode == "none":
        logger.info("Auth disabled, using NoAuthHandler")
        return NoAuthHandler(config)

    # Look up handler class
    handler_class = _AUTH_HANDLERS.get(mode)

    if not handler_class:
        available = ", ".join(_AUTH_HANDLERS.keys())
        raise ValueError(f"Unsupported auth mode: '{mode}'. Available modes: {available}")

    # Special handling for JWT - check dependencies
    if mode == "jwt" and "jwt" not in _AUTH_HANDLERS:
        raise ImportError(
            "JWT authentication requires PyJWT. Install with: pip install PyJWT[crypto]"
        )

    # Create handler instance
    logger.info(f"Creating auth handler: mode={mode}")

    try:
        handler = handler_class(config)
        logger.info(
            f"Auth handler initialized: {handler.__class__.__name__}",
            extra={"mode": mode, "enabled": config.enabled},
        )
        return handler

    except Exception as e:
        logger.error(f"Failed to create auth handler: {e}")
        raise


def get_available_auth_modes() -> list[str]:
    """
    Get list of available authentication modes.

    Returns:
        List of mode names that can be used
    """
    return list(_AUTH_HANDLERS.keys())


def register_auth_handler(mode: str, handler_class: Type[BaseAuthHandler]) -> None:
    """
    Register a custom auth handler.

    This allows extending the auth system with custom handlers
    without modifying the core module.

    Args:
        mode: The mode name to register
        handler_class: The handler class (must extend BaseAuthHandler)

    Example:
        >>> class CustomAuthHandler(BaseAuthHandler):
        ...     async def authenticate(self, request):
        ...         # Custom logic
        ...         pass

        >>> register_auth_handler("custom", CustomAuthHandler)
    """
    if not issubclass(handler_class, BaseAuthHandler):
        raise TypeError(f"Handler must extend BaseAuthHandler, got {handler_class}")

    _AUTH_HANDLERS[mode] = handler_class
    logger.info(f"Registered custom auth handler: {mode}")
