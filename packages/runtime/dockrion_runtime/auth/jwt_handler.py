"""
JWT Authentication Handler for Dockrion Runtime

Provides enterprise-grade JWT authentication with:
- JWKS (JSON Web Key Set) support for key rotation
- RS256/ES256 signature verification
- Standard claim validation (iss, aud, exp, nbf)
- Custom claim extraction for identity context
- Key caching with configurable refresh
"""

import os
import time
import threading
from typing import Optional, Dict, Any, List
from urllib.request import urlopen
from urllib.error import URLError
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fastapi import Request

from dockrion_common.logger import get_logger

from .base import BaseAuthHandler, AuthConfig
from .context import AuthContext
from .exceptions import (
    MissingCredentialsError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenValidationError,
    ConfigurationError,
)

logger = get_logger(__name__)

# Try to import JWT libraries
try:
    import jwt
    from jwt import PyJWKClient, PyJWKClientError
    from jwt.exceptions import (
        InvalidTokenError,
        ExpiredSignatureError,
        InvalidAudienceError,
        InvalidIssuerError,
        DecodeError,
    )
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning(
        "PyJWT not installed. JWT authentication will not be available. "
        "Install with: pip install PyJWT[crypto]"
    )


@dataclass
class JWKSCache:
    """
    Cache for JWKS (JSON Web Key Set).
    
    Caches keys for performance while supporting refresh
    for key rotation scenarios.
    """
    keys: Dict[str, Any] = field(default_factory=dict)
    last_refresh: Optional[datetime] = None
    refresh_interval: timedelta = field(default_factory=lambda: timedelta(hours=1))
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def is_stale(self) -> bool:
        """Check if cache needs refresh."""
        if not self.last_refresh:
            return True
        return datetime.utcnow() - self.last_refresh > self.refresh_interval


class JWTAuthHandler(BaseAuthHandler):
    """
    JWT authentication handler with JWKS support.
    
    Supports:
    - JWKS URL for automatic key rotation (recommended)
    - Static public key via environment variable
    - RS256, RS384, RS512, ES256, ES384, ES512 algorithms
    - Standard JWT claims validation
    - Custom claim extraction
    
    Example config:
    ```yaml
    auth:
      mode: jwt
      jwt:
        # JWKS URL (recommended for production)
        jwks_url: https://auth.company.com/.well-known/jwks.json
        
        # OR static public key
        # public_key_env: JWT_PUBLIC_KEY
        
        # Validation
        issuer: https://auth.company.com/
        audience: my-agent-api
        algorithms: ["RS256"]
        leeway_seconds: 30
        
        # Claim mappings
        claims:
          user_id: sub
          email: email
          roles: permissions
          tenant_id: "org.tenant_id"  # Nested claim
    ```
    """
    
    def __init__(self, config: AuthConfig):
        if not JWT_AVAILABLE:
            raise ImportError(
                "PyJWT is required for JWT authentication. "
                "Install with: pip install PyJWT[crypto]"
            )
        
        super().__init__(config)
        
        # JWKS client for key fetching
        self._jwks_client: Optional[PyJWKClient] = None
        
        # Static public key (alternative to JWKS)
        self._static_public_key: Optional[str] = None
        
        # JWKS cache
        self._jwks_cache = JWKSCache(
            refresh_interval=timedelta(hours=1)
        )
        
        # Initialize key source
        self._init_key_source()
    
    def _init_key_source(self) -> None:
        """Initialize JWKS client or load static key."""
        if self.config.jwt_jwks_url:
            try:
                self._jwks_client = PyJWKClient(
                    self.config.jwt_jwks_url,
                    cache_keys=True,
                    lifespan=3600  # 1 hour cache
                )
                logger.info(
                    f"Initialized JWKS client: {self.config.jwt_jwks_url}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize JWKS client: {e}")
                raise ConfigurationError(
                    f"Failed to initialize JWKS from {self.config.jwt_jwks_url}: {e}"
                )
        
        elif self.config.jwt_public_key_env:
            self._static_public_key = os.environ.get(
                self.config.jwt_public_key_env
            )
            if not self._static_public_key:
                logger.error(
                    f"JWT public key not found in {self.config.jwt_public_key_env}"
                )
                raise ConfigurationError(
                    f"JWT public key environment variable "
                    f"{self.config.jwt_public_key_env} not set"
                )
            logger.info(
                f"Loaded static public key from {self.config.jwt_public_key_env}"
            )
        
        else:
            raise ConfigurationError(
                "JWT authentication requires either 'jwks_url' or 'public_key_env'. "
                "Neither was provided."
            )
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT from Authorization header.
        
        Expected format: Authorization: Bearer <token>
        """
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        
        return None
    
    def _get_signing_key(self, token: str) -> Any:
        """
        Get the signing key for token verification.
        
        For JWKS: Extracts kid from token header and fetches key
        For static key: Returns the configured public key
        """
        if self._jwks_client:
            try:
                return self._jwks_client.get_signing_key_from_jwt(token)
            except PyJWKClientError as e:
                logger.error(f"Failed to get signing key from JWKS: {e}")
                raise TokenValidationError(
                    f"Failed to get signing key: {e}",
                    details={"error": str(e)}
                )
        
        elif self._static_public_key:
            return self._static_public_key
        
        raise ConfigurationError("No signing key source configured")
    
    def _decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT.
        
        Validates:
        - Signature using JWKS or static key
        - Expiration (exp claim)
        - Not Before (nbf claim)
        - Issuer (iss claim) if configured
        - Audience (aud claim) if configured
        """
        try:
            # Get signing key
            signing_key = self._get_signing_key(token)
            
            # Build decode options
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "require": ["exp", "iat"]
            }
            
            if self.config.jwt_issuer:
                options["verify_iss"] = True
            if self.config.jwt_audience:
                options["verify_aud"] = True
            
            # Decode token
            key = signing_key.key if hasattr(signing_key, 'key') else signing_key
            
            claims = jwt.decode(
                token,
                key,
                algorithms=self.config.jwt_algorithms,
                issuer=self.config.jwt_issuer,
                audience=self.config.jwt_audience,
                leeway=self.config.jwt_leeway_seconds,
                options=options
            )
            
            return claims
        
        except ExpiredSignatureError:
            raise TokenExpiredError(
                "JWT has expired",
                details={"hint": "Request a new token from your identity provider"}
            )
        
        except InvalidAudienceError:
            raise TokenValidationError(
                f"Invalid audience. Expected: {self.config.jwt_audience}",
                details={"expected_audience": self.config.jwt_audience}
            )
        
        except InvalidIssuerError:
            raise TokenValidationError(
                f"Invalid issuer. Expected: {self.config.jwt_issuer}",
                details={"expected_issuer": self.config.jwt_issuer}
            )
        
        except DecodeError as e:
            raise TokenValidationError(
                f"Failed to decode JWT: {e}",
                details={"error": str(e)}
            )
        
        except InvalidTokenError as e:
            raise TokenValidationError(
                f"Invalid JWT: {e}",
                details={"error": str(e)}
            )
    
    async def authenticate(self, request: Request) -> AuthContext:
        """
        Authenticate request using JWT.
        
        Args:
            request: FastAPI request
            
        Returns:
            AuthContext with user identity from claims
            
        Raises:
            MissingCredentialsError: If no token provided
            TokenExpiredError: If token has expired
            TokenValidationError: If token is invalid
        """
        # Extract token
        token = self._extract_token(request)
        
        if not token:
            raise MissingCredentialsError(
                "JWT required. Provide via 'Authorization: Bearer <token>' header"
            )
        
        # Decode and validate token
        claims = self._decode_token(token)
        
        # Build auth context from claims
        context = AuthContext.from_jwt(
            claims=claims,
            claim_mappings=self.config.jwt_claim_mappings or None
        )
        
        logger.debug(
            f"Authenticated JWT for user: {context.user_id}",
            extra={
                "user_id": context.user_id,
                "roles": context.roles,
                "client_id": context.client_id
            }
        )
        
        return context
    
    def get_auth_scheme(self) -> str:
        return "bearer"
    
    def get_auth_description(self) -> str:
        return "JWT Bearer token authentication via 'Authorization: Bearer <token>' header"
    
    async def health_check(self) -> bool:
        """
        Check if JWKS endpoint is reachable.
        
        For static key, always returns True.
        """
        if self._static_public_key:
            return True
        
        if self._jwks_client and self.config.jwt_jwks_url:
            try:
                # Try to fetch JWKS
                with urlopen(self.config.jwt_jwks_url, timeout=5) as response:
                    return response.status == 200
            except URLError as e:
                logger.error(f"JWKS health check failed: {e}")
                return False
        
        return False
    
    async def refresh_keys(self) -> None:
        """
        Force refresh of JWKS keys.
        
        Called periodically or on key verification failure.
        """
        if self._jwks_client:
            try:
                # PyJWKClient handles caching internally
                # We just need to clear its cache
                self._jwks_client = PyJWKClient(
                    self.config.jwt_jwks_url,
                    cache_keys=True,
                    lifespan=3600
                )
                self._jwks_cache.last_refresh = datetime.utcnow()
                logger.info("Refreshed JWKS keys")
            except Exception as e:
                logger.error(f"Failed to refresh JWKS keys: {e}")

