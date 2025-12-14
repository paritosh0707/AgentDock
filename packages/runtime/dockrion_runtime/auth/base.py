"""
Base Authentication Handler for Dockrion Runtime

Defines the abstract interface for all authentication handlers.
All auth implementations must inherit from BaseAuthHandler.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from fastapi import Request

from .context import AuthContext


@dataclass
class AuthConfig:
    """
    Configuration for authentication handlers.
    
    This is the runtime configuration extracted from DockSpec.auth,
    not the schema model itself.
    """
    
    # Core settings
    enabled: bool = True
    mode: str = "api_key"
    
    # API Key settings
    api_key_env_var: str = "DOCKRION_API_KEY"
    api_key_header: str = "X-API-Key"
    api_key_prefix: Optional[str] = None  # For multi-key: "AGENT_KEY_"
    allow_bearer: bool = True  # Allow Authorization: Bearer <key>
    
    # JWT settings
    jwt_jwks_url: Optional[str] = None
    jwt_public_key_env: Optional[str] = None  # Alternative to JWKS
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    jwt_algorithms: List[str] = field(default_factory=lambda: ["RS256"])
    jwt_claim_mappings: Dict[str, str] = field(default_factory=dict)
    jwt_leeway_seconds: int = 30  # Clock skew tolerance
    
    # OAuth2 settings (future)
    oauth2_introspection_url: Optional[str] = None
    oauth2_client_id_env: Optional[str] = None
    oauth2_client_secret_env: Optional[str] = None
    oauth2_required_scopes: List[str] = field(default_factory=list)
    
    # RBAC settings
    roles: List[Dict[str, Any]] = field(default_factory=list)
    role_claim_path: str = "roles"  # Where to find roles in JWT
    
    # Rate limiting
    rate_limits: Dict[str, str] = field(default_factory=dict)  # role -> "100/minute"
    
    # Key metadata (for multi-key API key auth)
    key_metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, config: Optional[Dict[str, Any]]) -> "AuthConfig":
        """Create AuthConfig from dictionary (usually from DockSpec)."""
        if not config:
            return cls(enabled=False, mode="none")
        
        mode = config.get("mode", "api_key")
        enabled = mode != "none"
        
        # Extract API key config
        api_keys_config = config.get("api_keys", {})
        if isinstance(api_keys_config, dict):
            api_key_env_var = api_keys_config.get("env_var", "DOCKRION_API_KEY")
            api_key_header = api_keys_config.get("header", "X-API-Key")
            api_key_prefix = api_keys_config.get("prefix")
        else:
            api_key_env_var = "DOCKRION_API_KEY"
            api_key_header = "X-API-Key"
            api_key_prefix = None
        
        # Extract JWT config
        jwt_config = config.get("jwt", {})
        if isinstance(jwt_config, dict):
            jwt_jwks_url = jwt_config.get("jwks_url")
            jwt_public_key_env = jwt_config.get("public_key_env")
            jwt_issuer = jwt_config.get("issuer")
            jwt_audience = jwt_config.get("audience")
            jwt_algorithms = jwt_config.get("algorithms", ["RS256"])
            jwt_claim_mappings = jwt_config.get("claims", {})
            jwt_leeway = jwt_config.get("leeway_seconds", 30)
        else:
            jwt_jwks_url = None
            jwt_public_key_env = None
            jwt_issuer = None
            jwt_audience = None
            jwt_algorithms = ["RS256"]
            jwt_claim_mappings = {}
            jwt_leeway = 30
        
        # Extract OAuth2 config (future)
        oauth2_config = config.get("oauth2", {})
        if isinstance(oauth2_config, dict):
            oauth2_introspection_url = oauth2_config.get("introspection_url")
            oauth2_client_id_env = oauth2_config.get("client_id_env")
            oauth2_client_secret_env = oauth2_config.get("client_secret_env")
            oauth2_required_scopes = oauth2_config.get("required_scopes", [])
        else:
            oauth2_introspection_url = None
            oauth2_client_id_env = None
            oauth2_client_secret_env = None
            oauth2_required_scopes = []
        
        # Extract RBAC
        roles = config.get("roles", [])
        rate_limits = config.get("rate_limits", {})
        
        return cls(
            enabled=enabled,
            mode=mode,
            api_key_env_var=api_key_env_var,
            api_key_header=api_key_header,
            api_key_prefix=api_key_prefix,
            jwt_jwks_url=jwt_jwks_url,
            jwt_public_key_env=jwt_public_key_env,
            jwt_issuer=jwt_issuer,
            jwt_audience=jwt_audience,
            jwt_algorithms=jwt_algorithms,
            jwt_claim_mappings=jwt_claim_mappings,
            jwt_leeway_seconds=jwt_leeway,
            oauth2_introspection_url=oauth2_introspection_url,
            oauth2_client_id_env=oauth2_client_id_env,
            oauth2_client_secret_env=oauth2_client_secret_env,
            oauth2_required_scopes=oauth2_required_scopes,
            roles=roles if isinstance(roles, list) else [],
            rate_limits=rate_limits if isinstance(rate_limits, dict) else {}
        )


class BaseAuthHandler(ABC):
    """
    Abstract base class for authentication handlers.
    
    All authentication implementations must:
    1. Inherit from this class
    2. Implement the authenticate() method
    3. Optionally override health_check()
    
    The handler lifecycle:
    1. Created once during app startup
    2. authenticate() called for each request
    3. Returns AuthContext on success, raises AuthError on failure
    """
    
    def __init__(self, config: AuthConfig):
        """
        Initialize handler with configuration.
        
        Args:
            config: Authentication configuration
        """
        self.config = config
    
    @abstractmethod
    async def authenticate(self, request: Request) -> AuthContext:
        """
        Authenticate an incoming request.
        
        This is the main entry point for authentication. Implementations should:
        1. Extract credentials from the request (headers, cookies, etc.)
        2. Validate the credentials
        3. Build and return an AuthContext on success
        4. Raise appropriate AuthError subclass on failure
        
        Args:
            request: FastAPI Request object
            
        Returns:
            AuthContext with identity information
            
        Raises:
            MissingCredentialsError: If credentials not provided
            InvalidCredentialsError: If credentials are invalid
            TokenExpiredError: If token has expired
            ConfigurationError: If auth is misconfigured
        """
        pass
    
    def get_auth_scheme(self) -> str:
        """
        Get the authentication scheme name (for OpenAPI docs).
        
        Returns:
            Scheme name like "apiKey", "bearer", "oauth2"
        """
        return "apiKey"
    
    def get_auth_description(self) -> str:
        """
        Get human-readable description of auth requirements.
        
        Returns:
            Description for API documentation
        """
        return "Authentication required"
    
    async def health_check(self) -> bool:
        """
        Check if auth handler is healthy.
        
        Override to add checks like:
        - JWKS endpoint reachability
        - OAuth2 introspection endpoint availability
        - Vault connectivity
        
        Returns:
            True if healthy, False otherwise
        """
        return True
    
    async def refresh_keys(self) -> None:
        """
        Refresh cached keys/configuration.
        
        Override for handlers that cache external data like JWKS.
        Called periodically by the runtime.
        """
        pass


class NoAuthHandler(BaseAuthHandler):
    """
    Passthrough handler that allows all requests.
    
    Used when auth.mode is "none" or not configured.
    Returns an anonymous context for all requests.
    """
    
    def __init__(self, config: Optional[AuthConfig] = None):
        super().__init__(config or AuthConfig(enabled=False, mode="none"))
    
    async def authenticate(self, request: Request) -> AuthContext:
        """Always returns anonymous context."""
        return AuthContext.anonymous()
    
    def get_auth_scheme(self) -> str:
        return "none"
    
    def get_auth_description(self) -> str:
        return "No authentication required"

