"""
Authentication for Dockrion Runtime

Provides API key and token validation.
"""

import os
from typing import Optional
from fastapi import Request, HTTPException

from dockrion_common.logger import get_logger

logger = get_logger(__name__)


class AuthHandler:
    """
    Handles authentication for the runtime.
    
    Supports:
        - API key authentication (via X-API-Key header or Bearer token)
        - No auth (passthrough mode)
    """
    
    def __init__(
        self,
        enabled: bool = False,
        mode: str = "none",
        env_var: str = "DOCKRION_API_KEY"
    ):
        """
        Initialize auth handler.
        
        Args:
            enabled: Whether auth is enabled
            mode: Auth mode ("api_key", "jwt", "none")
            env_var: Environment variable containing the valid API key
        """
        self.enabled = enabled
        self.mode = mode
        self.env_var = env_var
    
    async def verify(self, request: Request) -> Optional[str]:
        """
        Verify authentication for a request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            API key if valid, None if auth disabled
            
        Raises:
            HTTPException: If auth fails (401)
        """
        if not self.enabled or self.mode == "none":
            return None
        
        if self.mode == "api_key":
            return await self._verify_api_key(request)
        
        # Unsupported auth mode - fail open with warning
        logger.warning(f"Unsupported auth mode: {self.mode}, allowing request")
        return None
    
    async def _verify_api_key(self, request: Request) -> str:
        """Verify API key from request headers."""
        # Check X-API-Key header first
        api_key = request.headers.get("X-API-Key")
        
        # Fall back to Authorization: Bearer <key>
        if not api_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
        
        if not api_key:
            logger.warning("Missing API key in request")
            raise HTTPException(
                status_code=401,
                detail="Missing API key. Provide via X-API-Key header or Authorization: Bearer <key>"
            )
        
        # Validate against environment variable
        valid_key = os.environ.get(self.env_var, "")
        if not valid_key:
            logger.error(f"API key validation failed: {self.env_var} not set")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: API key not configured"
            )
        
        if api_key != valid_key:
            logger.warning("Invalid API key provided")
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        return api_key


def create_auth_handler(auth_config: Optional[dict]) -> AuthHandler:
    """
    Factory function to create AuthHandler from config.
    
    Args:
        auth_config: Auth section from DockSpec
        
    Returns:
        Configured AuthHandler instance
    """
    if not auth_config:
        return AuthHandler(enabled=False)
    
    mode = auth_config.get("mode", "none")
    enabled = mode != "none"
    
    return AuthHandler(enabled=enabled, mode=mode)

