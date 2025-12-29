"""
API Key Authentication Handler for Dockrion Runtime

Provides enterprise-grade API key authentication with:
- Single key mode (simple)
- Multi-key mode (multiple keys with identifiers)
- Key metadata and role assignment
- Secure key comparison (timing-safe)
"""

import hashlib
import os
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dockrion_common.logger import get_logger
from fastapi import Request

from .base import AuthConfig, BaseAuthHandler
from .context import AuthContext
from .exceptions import (
    ConfigurationError,
    InvalidCredentialsError,
    MissingCredentialsError,
)

logger = get_logger(__name__)


@dataclass
class ApiKeyMetadata:
    """
    Metadata associated with an API key.

    Attributes:
        key_id: Unique identifier for this key
        name: Human-readable name
        roles: Roles assigned to this key
        permissions: Explicit permissions
        rate_limit: Rate limit for this key
        metadata: Custom metadata
    """

    key_id: str
    name: str = ""
    roles: List[str] = field(default_factory=lambda: ["default"])
    permissions: List[str] = field(default_factory=lambda: ["invoke"])
    rate_limit: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Internal: hashed key for secure storage (optional)
    key_hash: Optional[str] = None


class ApiKeyAuthHandler(BaseAuthHandler):
    """
    API Key authentication handler.

    Supports two modes:

    1. **Single Key Mode** (simple):
       - One API key in environment variable
       - Default for most use cases
       - Config: `api_keys.env_var: MY_API_KEY`

    2. **Multi-Key Mode** (enterprise):
       - Multiple keys with prefix pattern
       - Each key has an ID and metadata
       - Config: `api_keys.prefix: AGENT_KEY_`
       - Keys: AGENT_KEY_PROD, AGENT_KEY_DEV, etc.

    Headers accepted:
    - X-API-Key: <key>
    - Authorization: Bearer <key>

    Example config:
    ```yaml
    auth:
      mode: api_key
      api_keys:
        env_var: MY_AGENT_KEY        # Single key
        # OR
        prefix: AGENT_KEY_            # Multi-key
        header: X-API-Key            # Custom header
    ```
    """

    def __init__(self, config: AuthConfig):
        super().__init__(config)

        # Loaded keys: plaintext_key -> ApiKeyMetadata
        self._keys: Dict[str, ApiKeyMetadata] = {}

        # Flag for multi-key mode
        self._multi_key_mode: bool = False

        # Load keys on init
        self._load_keys()

    def _load_keys(self) -> None:
        """
        Load API keys from environment.

        In single-key mode, loads from api_key_env_var.
        In multi-key mode, scans for keys matching prefix pattern.
        """
        if self.config.api_key_prefix:
            self._load_multi_keys()
        else:
            self._load_single_key()

        if not self._keys:
            logger.warning(
                "No API keys loaded. Auth will fail for all requests. "
                f"Set {self.config.api_key_env_var} or keys with prefix {self.config.api_key_prefix}"
            )

    def _load_single_key(self) -> None:
        """Load single API key from environment variable."""
        key = os.environ.get(self.config.api_key_env_var, "").strip()

        if key:
            self._keys[key] = ApiKeyMetadata(
                key_id="default",
                name="Default API Key",
                roles=["default"],
                permissions=["invoke", "view_metrics"],
            )
            logger.info(
                f"Loaded API key from {self.config.api_key_env_var}", extra={"key_id": "default"}
            )
        else:
            logger.warning(f"API key environment variable {self.config.api_key_env_var} not set")

    def _load_multi_keys(self) -> None:
        """Load multiple API keys matching prefix pattern."""
        self._multi_key_mode = True
        prefix = self.config.api_key_prefix or ""

        # Scan environment for matching keys
        for env_name, env_value in os.environ.items():
            if prefix and env_name.startswith(prefix):
                key_id = env_name[len(prefix) :]  # Extract ID from var name
                key_value = env_value.strip()

                if key_value:
                    # Check for metadata config
                    metadata_config = self.config.key_metadata.get(key_id, {})

                    self._keys[key_value] = ApiKeyMetadata(
                        key_id=key_id,
                        name=metadata_config.get("name", f"Key {key_id}"),
                        roles=metadata_config.get("roles", ["default"]),
                        permissions=metadata_config.get("permissions", ["invoke"]),
                        rate_limit=metadata_config.get("rate_limit"),
                        metadata=metadata_config.get("metadata", {}),
                    )
                    logger.info(
                        f"Loaded API key {key_id} from {env_name}", extra={"key_id": key_id}
                    )

        logger.info(f"Loaded {len(self._keys)} API keys with prefix {prefix}")

    def _extract_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request headers.

        Checks in order:
        1. Custom header (default: X-API-Key)
        2. Authorization: Bearer <key>

        Args:
            request: FastAPI request

        Returns:
            Extracted key or None
        """
        # Check custom header first
        header_name = self.config.api_key_header or "X-API-Key"
        api_key = request.headers.get(header_name)

        if api_key:
            return api_key.strip()

        # Check Authorization: Bearer header
        if self.config.allow_bearer:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                return auth_header[7:].strip()

        return None

    def _validate_key(self, key: str) -> Optional[ApiKeyMetadata]:
        """
        Validate API key using timing-safe comparison.

        Args:
            key: The key to validate

        Returns:
            ApiKeyMetadata if valid, None otherwise
        """
        # Use timing-safe comparison to prevent timing attacks
        for stored_key, metadata in self._keys.items():
            if secrets.compare_digest(key, stored_key):
                return metadata
        return None

    async def authenticate(self, request: Request) -> AuthContext:
        """
        Authenticate request using API key.

        Args:
            request: FastAPI request

        Returns:
            AuthContext with key identity

        Raises:
            MissingCredentialsError: If no key provided
            InvalidCredentialsError: If key is invalid
            ConfigurationError: If no keys configured
        """
        # Check configuration
        if not self._keys:
            logger.error("No API keys configured")
            raise ConfigurationError(
                "API key authentication not configured. "
                f"Set environment variable: {self.config.api_key_env_var}"
            )

        # Extract key from request
        api_key = self._extract_key(request)

        if not api_key:
            header_name = self.config.api_key_header or "X-API-Key"
            raise MissingCredentialsError(
                f"API key required. Provide via '{header_name}' header "
                "or 'Authorization: Bearer <key>'"
            )

        # Validate key
        metadata = self._validate_key(api_key)

        if not metadata:
            logger.warning(
                "Invalid API key attempted",
                extra={
                    "path": request.url.path,
                    "key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "***",
                },
            )
            raise InvalidCredentialsError("Invalid API key")

        # Build auth context
        logger.debug(
            f"Authenticated with API key: {metadata.key_id}",
            extra={"key_id": metadata.key_id, "roles": metadata.roles},
        )

        return AuthContext.from_api_key(
            key_id=metadata.key_id,
            roles=metadata.roles,
            permissions=metadata.permissions,
            metadata={
                "name": metadata.name,
                "rate_limit": metadata.rate_limit,
                **metadata.metadata,
            },
        )

    def get_auth_scheme(self) -> str:
        return "apiKey"

    def get_auth_description(self) -> str:
        header = self.config.api_key_header or "X-API-Key"
        return f"API key authentication via '{header}' header or 'Authorization: Bearer <key>'"

    async def health_check(self) -> bool:
        """Check if at least one key is configured."""
        return len(self._keys) > 0

    def get_key_count(self) -> int:
        """Get number of configured keys."""
        return len(self._keys)

    def get_key_ids(self) -> List[str]:
        """Get list of configured key IDs."""
        return [m.key_id for m in self._keys.values()]


def generate_api_key(prefix: str = "sk", length: int = 32) -> str:
    """
    Generate a secure random API key.

    Format: {prefix}_{random_hex}
    Example: sk_a1b2c3d4e5f6...

    Args:
        prefix: Key prefix (default: "sk")
        length: Length of random portion in bytes (default: 32)

    Returns:
        Generated API key string
    """
    random_part = secrets.token_hex(length)
    return f"{prefix}_{random_part}"


def hash_api_key(key: str) -> str:
    """
    Hash an API key for secure storage.

    Uses SHA-256 for consistent, non-reversible hashing.
    This is useful for audit logs and key metadata storage.

    Args:
        key: The plaintext API key

    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(key.encode()).hexdigest()
