"""
Authentication Context for Dockrion Runtime

Provides a unified identity context that flows through the request lifecycle.
This context is populated by auth handlers and made available to agents/handlers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AuthMethod(Enum):
    """Authentication method used."""

    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    MTLS = "mtls"  # Future


@dataclass
class AuthContext:
    """
    Authentication context carrying identity information.

    This context is:
    - Created by auth handlers upon successful authentication
    - Attached to the request state
    - Available to agents/handlers for identity-aware processing
    - Used for audit logging and metrics

    Attributes:
        authenticated: Whether request was authenticated
        method: Authentication method used
        identity_id: Unique identifier for the identity (key_id, user_id, client_id)
        identity_type: Type of identity ("api_key", "user", "service")

        # User-specific (from JWT claims)
        user_id: User identifier (from 'sub' claim or equivalent)
        email: User email if available
        name: User display name if available

        # Authorization
        roles: List of role names
        permissions: List of permission strings
        scopes: OAuth2 scopes if applicable

        # Metadata
        key_id: API key identifier (for multi-key setups)
        client_id: OAuth2 client identifier
        tenant_id: Multi-tenant identifier if applicable

        # Audit trail
        authenticated_at: When authentication occurred
        token_expires_at: When token/session expires
        metadata: Additional custom metadata
    """

    # Core authentication state
    authenticated: bool = False
    method: AuthMethod = AuthMethod.NONE

    # Identity
    identity_id: Optional[str] = None
    identity_type: str = "anonymous"

    # User info (from JWT/OAuth)
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None

    # Authorization
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)

    # Identifiers
    key_id: Optional[str] = None
    client_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # Temporal
    authenticated_at: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None

    # Extension point
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def anonymous(cls) -> "AuthContext":
        """Create an anonymous (unauthenticated) context."""
        return cls(authenticated=False, method=AuthMethod.NONE, identity_type="anonymous")

    @classmethod
    def from_api_key(
        cls,
        key_id: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AuthContext":
        """
        Create context from API key authentication.

        Args:
            key_id: Identifier for the API key
            roles: Roles associated with this key
            permissions: Permissions granted to this key
            metadata: Additional key metadata
        """
        return cls(
            authenticated=True,
            method=AuthMethod.API_KEY,
            identity_id=key_id,
            identity_type="api_key",
            key_id=key_id,
            roles=roles or ["default"],
            permissions=permissions or ["invoke"],
            authenticated_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    @classmethod
    def from_jwt(
        cls, claims: Dict[str, Any], claim_mappings: Optional[Dict[str, str]] = None
    ) -> "AuthContext":
        """
        Create context from JWT claims.

        Args:
            claims: Decoded JWT claims
            claim_mappings: Mapping of context fields to claim paths
                e.g., {"user_id": "sub", "email": "email", "roles": "permissions"}
        """
        mappings = claim_mappings or {
            "user_id": "sub",
            "email": "email",
            "name": "name",
            "roles": "roles",
            "permissions": "permissions",
            "scopes": "scope",
        }

        def get_claim(claim_path: str) -> Any:
            """Get nested claim value using dot notation."""
            value: Any = claims
            for part in claim_path.split("."):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value

        user_id = get_claim(mappings.get("user_id", "sub"))

        # Handle scope as space-separated string or list
        scopes = get_claim(mappings.get("scopes", "scope"))
        if isinstance(scopes, str):
            scopes = scopes.split()
        elif not isinstance(scopes, list):
            scopes = []

        # Handle roles/permissions as list
        roles = get_claim(mappings.get("roles", "roles"))
        if not isinstance(roles, list):
            roles = [roles] if roles else []

        permissions = get_claim(mappings.get("permissions", "permissions"))
        if not isinstance(permissions, list):
            permissions = [permissions] if permissions else []

        # Extract expiry
        exp = claims.get("exp")
        expires_at = datetime.fromtimestamp(exp) if exp else None

        return cls(
            authenticated=True,
            method=AuthMethod.JWT,
            identity_id=user_id,
            identity_type="user",
            user_id=user_id,
            email=get_claim(mappings.get("email", "email")),
            name=get_claim(mappings.get("name", "name")),
            roles=roles,
            permissions=permissions,
            scopes=scopes,
            client_id=claims.get("azp") or claims.get("client_id"),
            tenant_id=get_claim(mappings.get("tenant_id", "tenant_id")),
            authenticated_at=datetime.utcnow(),
            token_expires_at=expires_at,
            metadata={"claims": claims},
        )

    @classmethod
    def from_oauth2(
        cls,
        client_id: str,
        scopes: List[str],
        subject: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AuthContext":
        """
        Create context from OAuth2 token introspection.

        Args:
            client_id: OAuth2 client identifier
            scopes: Granted scopes
            subject: Token subject (user or service)
            metadata: Additional token metadata
        """
        return cls(
            authenticated=True,
            method=AuthMethod.OAUTH2,
            identity_id=subject or client_id,
            identity_type="service" if not subject else "user",
            user_id=subject,
            client_id=client_id,
            scopes=scopes,
            authenticated_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    def has_role(self, role: str) -> bool:
        """Check if context has a specific role."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if context has a specific permission."""
        return permission in self.permissions

    def has_scope(self, scope: str) -> bool:
        """Check if context has a specific OAuth2 scope."""
        return scope in self.scopes

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if context has any of the specified roles."""
        return bool(set(self.roles) & set(roles))

    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if context has all specified permissions."""
        return set(permissions).issubset(set(self.permissions))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "authenticated": self.authenticated,
            "method": self.method.value,
            "identity_id": self.identity_id,
            "identity_type": self.identity_type,
            "user_id": self.user_id,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "scopes": self.scopes,
            "key_id": self.key_id,
            "client_id": self.client_id,
            "tenant_id": self.tenant_id,
        }

    def to_log_safe_dict(self) -> Dict[str, Any]:
        """Convert to dictionary safe for logging (no PII)."""
        return {
            "authenticated": self.authenticated,
            "method": self.method.value,
            "identity_type": self.identity_type,
            "roles": self.roles,
            "has_permissions": len(self.permissions) > 0,
            "scopes": self.scopes,
        }
