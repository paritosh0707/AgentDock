"""
dockrion Dockfile Schema v1.0

This module defines Pydantic models for validating Dockfile configurations.
It provides type-safe validation for all Dockfile sections.

Design Principles:
- Pure validation: Receives dicts, validates structure, returns typed objects
- No file I/O: File reading/writing is SDK's responsibility
- Extensible: Accepts unknown fields for future expansion
- Security-first: Critical validations prevent code injection

Usage:
    from dockrion_schema import DockSpec

    # SDK passes parsed dict to schema for validation
    data = {"version": "1.0", "agent": {...}, ...}
    spec = DockSpec.model_validate(data)
"""

import re
from typing import Any, Dict, List, Literal, Optional, Union

# Import validation utilities and constants from common package
from dockrion_common import (
    LOG_LEVELS,
    PERMISSIONS,
    SUPPORTED_AUTH_MODES,
    SUPPORTED_DOCKFILE_VERSIONS,
    SUPPORTED_FRAMEWORKS,
    SUPPORTED_STREAMING,
    RuntimeDefaults,
    ValidationError,
    parse_rate_limit,
    validate_agent_name,
    validate_entrypoint,
    validate_handler,
    validate_port,
)
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing_extensions import Self

# =============================================================================
# I/O SCHEMA MODELS
# =============================================================================


class IOSubSchema(BaseModel):
    """
    JSON Schema definition for input or output.

    Defines the structure of data that agents receive or return.
    Supports basic JSON Schema types: object, string, number, integer, boolean, array.

    Note: Properties should be valid JSON Schema definitions. Nested objects
    and arrays are supported through recursive schema definitions.
    """

    type: str = "object"  # Validated against JSON_SCHEMA_TYPES
    properties: Dict[str, Any] = {}  # Can contain nested schemas
    required: List[str] = []
    items: Optional[Dict[str, Any]] = None  # For array types
    description: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate JSON Schema type is supported"""
        # Common JSON Schema types
        SUPPORTED_TYPES = ["object", "string", "number", "integer", "boolean", "array", "null"]
        if v not in SUPPORTED_TYPES:
            raise ValidationError(
                f"Unsupported JSON Schema type: '{v}'. "
                f"Supported types: {', '.join(SUPPORTED_TYPES)}"
            )
        return v

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate properties are valid JSON Schema definitions"""
        if not isinstance(v, dict):
            raise ValidationError("properties must be a dictionary")

        # Basic validation: each property should have a type
        for prop_name, prop_schema in v.items():
            if not isinstance(prop_schema, dict):
                raise ValidationError(
                    f"Property '{prop_name}' must be a JSON Schema object (dict), got {type(prop_schema).__name__}"
                )

            # Validate property name is not empty
            if not prop_name or not prop_name.strip():
                raise ValidationError("Property names cannot be empty or whitespace")

            # If property has a type, validate it's supported
            if "type" in prop_schema:
                prop_type = prop_schema["type"]
                SUPPORTED_TYPES = [
                    "object",
                    "string",
                    "number",
                    "integer",
                    "boolean",
                    "array",
                    "null",
                ]
                if prop_type not in SUPPORTED_TYPES:
                    raise ValidationError(
                        f"Property '{prop_name}' has unsupported type: '{prop_type}'. "
                        f"Supported types: {', '.join(SUPPORTED_TYPES)}"
                    )

                # If type is array, should have items
                if prop_type == "array" and "items" not in prop_schema:
                    raise ValidationError(
                        f"Property '{prop_name}' is type 'array' but missing 'items' definition"
                    )

        return v

    @field_validator("required")
    @classmethod
    def validate_required_fields(cls, v: List[str], info) -> List[str]:
        """Validate required fields exist in properties"""
        if not isinstance(v, list):
            raise ValidationError("required must be a list")

        # Check for duplicates
        if len(v) != len(set(v)):
            duplicates = [item for item in v if v.count(item) > 1]
            raise ValidationError(f"Duplicate fields in required list: {duplicates}")

        # Note: We can't validate against properties here because properties
        # might not be set yet during validation. This will be checked in
        # model_validator if needed.

        return v

    @model_validator(mode="after")
    def validate_required_in_properties(self) -> Self:
        """Validate all required fields are defined in properties"""
        if self.type == "object" and self.required:
            # Only validate if we have properties defined
            if self.properties:
                for required_field in self.required:
                    if required_field not in self.properties:
                        raise ValidationError(
                            f"Required field '{required_field}' is not defined in properties. "
                            f"Available properties: {', '.join(self.properties.keys())}"
                        )
        return self

    @model_validator(mode="after")
    def validate_array_has_items(self) -> Self:
        """Validate array types have items definition"""
        if self.type == "array" and not self.items:
            raise ValidationError(
                "JSON Schema type 'array' requires 'items' field to define array element type"
            )
        return self


class IOSchema(BaseModel):
    """
    Input/Output schema for agent invocation.

    Defines the contract for what the agent accepts and returns.
    Runtime uses this to validate requests and format responses.

    Attributes:
        strict: If False, skip output validation. Useful when output structure
                is dynamic or unknown. Defaults to True.
        input: Input schema definition (optional)
        output: Output schema definition (optional - if not provided, output is not validated)
    """

    strict: bool = True
    input: Optional[IOSubSchema] = None
    output: Optional[IOSubSchema] = None

    model_config = ConfigDict(extra="allow")


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================


class AgentConfig(BaseModel):
    """
    Agent metadata and code location.

    Supports two invocation modes:

    1. **Entrypoint Mode** (Framework Agents):
       - Uses `entrypoint` field pointing to a factory function
       - Factory returns an agent object with `.invoke()` method
       - Requires `framework` field (langgraph, langchain, etc.)

    2. **Handler Mode** (Service Functions):
       - Uses `handler` field pointing to a direct callable
       - Callable receives payload dict, returns response dict
       - Framework defaults to "custom"

    At least one of `entrypoint` or `handler` must be provided.
    If both are provided, `handler` takes precedence for invocation.

    Examples:
        # Entrypoint mode (LangGraph agent)
        agent:
          name: my-agent
          entrypoint: app.graph:build_graph
          framework: langgraph

        # Handler mode (custom service)
        agent:
          name: my-service
          handler: app.service:process_request
          framework: custom  # optional, defaults to custom
    """

    name: str
    description: Optional[str] = None

    # Entrypoint mode: factory function returning agent with .invoke()
    entrypoint: Optional[str] = None

    # Handler mode: direct callable function(payload) -> response
    handler: Optional[str] = None

    # Framework (required for entrypoint, defaults to "custom" for handler)
    framework: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate agent name format (lowercase, alphanumeric, hyphens)"""
        validate_agent_name(v)
        return v

    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint_format(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate entrypoint format and prevent code injection.

        Format: 'module.path:callable'
        Prevents: os.system:eval, ../../../etc/passwd:read
        """
        if v is not None:
            validate_entrypoint(v)
        return v

    @field_validator("handler")
    @classmethod
    def validate_handler_format(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate handler format.

        Format: 'module.path:callable'
        Handler must be a callable: def handler(payload: dict) -> dict
        """
        if v is not None:
            validate_handler(v)
        return v

    @field_validator("framework")
    @classmethod
    def validate_framework_supported(cls, v: Optional[str]) -> Optional[str]:
        """Validate framework is supported (uses SUPPORTED_FRAMEWORKS from common)"""
        if v is not None and v not in SUPPORTED_FRAMEWORKS:
            raise ValidationError(
                f"Unsupported framework: '{v}'. "
                f"Supported frameworks: {', '.join(SUPPORTED_FRAMEWORKS)}"
            )
        return v

    @model_validator(mode="after")
    def validate_entrypoint_or_handler(self) -> Self:
        """Ensure at least one of entrypoint or handler is provided."""
        if not self.entrypoint and not self.handler:
            raise ValidationError(
                "Agent must specify either 'entrypoint' (for framework agents) "
                "or 'handler' (for service functions). Neither was provided."
            )

        # Set default framework based on mode
        # Handler takes precedence when both are provided
        if self.framework is None:
            if self.handler:
                # Handler mode (or both specified): default to "custom"
                # When both are provided, handler takes precedence for invocation
                object.__setattr__(self, "framework", "custom")
            else:
                # Entrypoint-only mode requires explicit framework
                raise ValidationError(
                    "Agent with 'entrypoint' must specify 'framework'. "
                    f"Supported frameworks: {', '.join(SUPPORTED_FRAMEWORKS)}"
                )

        return self


# =============================================================================
# POLICY MODELS (Future - Phase 2)
# =============================================================================


class ToolPolicy(BaseModel):
    """
    Tool access control policy.

    NOTE: Policy enforcement happens in policy-engine package.
    Schema only validates the configuration.
    """

    allowed: List[str] = []
    deny_by_default: bool = True

    model_config = ConfigDict(extra="allow")


class SafetyPolicy(BaseModel):
    """
    Output safety and content filtering policy.

    NOTE: Redaction and filtering happen in policy-engine package.
    Schema only validates the configuration.
    """

    redact_patterns: List[str] = []
    max_output_chars: Optional[int] = None
    block_prompt_injection: bool = True
    halt_on_violation: bool = False

    model_config = ConfigDict(extra="allow")

    @field_validator("max_output_chars")
    @classmethod
    def validate_max_output_positive(cls, v: Optional[int]) -> Optional[int]:
        """Validate max_output_chars is positive"""
        if v is not None and v <= 0:
            raise ValidationError(f"max_output_chars must be positive. Got: {v}")
        return v


class Policies(BaseModel):
    """
    Security and safety policies.

    NOTE: These are optional in MVP. When policy-engine service is ready,
    these will be enforced at runtime.
    """

    tools: Optional[ToolPolicy] = None
    safety: Optional[SafetyPolicy] = None

    model_config = ConfigDict(extra="allow")


# =============================================================================
# AUTH CONFIGURATION
# =============================================================================


class RoleConfig(BaseModel):
    """
    Role-based access control configuration.

    Defines a named role with associated permissions.
    Roles can be assigned to API keys or extracted from JWT claims.

    Example:
        ```yaml
        roles:
          - name: admin
            permissions: [invoke, view_metrics, deploy, rollback]
          - name: operator
            permissions: [invoke, view_metrics]
        ```
    """

    name: str
    permissions: List[str]

    model_config = ConfigDict(extra="allow")

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: List[str]) -> List[str]:
        """Validate all permissions are recognized"""
        for perm in v:
            if perm not in PERMISSIONS:
                raise ValidationError(
                    f"Unknown permission: '{perm}'. Valid permissions: {', '.join(PERMISSIONS)}"
                )
        return v


class ApiKeysConfig(BaseModel):
    """
    API key authentication configuration.

    Supports two modes:
    - Single key: One key from env_var
    - Multi-key: Multiple keys matching prefix pattern

    Example (single key):
        ```yaml
        api_keys:
          env_var: MY_AGENT_KEY
          header: X-API-Key
        ```

    Example (multi-key):
        ```yaml
        api_keys:
          prefix: AGENT_KEY_  # Loads AGENT_KEY_PROD, AGENT_KEY_DEV, etc.
          header: X-API-Key
        ```
    """

    # Key source
    env_var: str = "DOCKRION_API_KEY"
    prefix: Optional[str] = None  # For multi-key mode

    # Request config
    header: str = "X-API-Key"
    allow_bearer: bool = True  # Allow Authorization: Bearer <key>

    # Key management (informational)
    enabled: bool = True
    rotation_days: Optional[int] = 30

    model_config = ConfigDict(extra="allow")

    @field_validator("rotation_days")
    @classmethod
    def validate_rotation_days_positive(cls, v: Optional[int]) -> Optional[int]:
        """Validate rotation_days is positive"""
        if v is not None and v <= 0:
            raise ValidationError(f"rotation_days must be positive. Got: {v}")
        return v

    @field_validator("header")
    @classmethod
    def validate_header_name(cls, v: str) -> str:
        """Validate header name is reasonable"""
        if not v or len(v) > 64:
            raise ValidationError("Header name must be 1-64 characters")
        return v


class JWTClaimsConfig(BaseModel):
    """
    JWT claim mapping configuration.

    Maps JWT claims to identity context fields.
    Supports nested claim paths with dot notation.

    Example:
        ```yaml
        claims:
          user_id: sub
          email: email
          roles: permissions
          tenant_id: org.tenant_id  # Nested claim
        ```
    """

    user_id: str = "sub"
    email: str = "email"
    name: str = "name"
    roles: str = "roles"
    permissions: str = "permissions"
    scopes: str = "scope"
    tenant_id: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JWTConfig(BaseModel):
    """
    JWT authentication configuration.

    Supports JWKS (recommended) or static public key.

    Example (JWKS - recommended):
        ```yaml
        jwt:
          jwks_url: https://auth.company.com/.well-known/jwks.json
          issuer: https://auth.company.com/
          audience: my-agent-api
          claims:
            user_id: sub
            roles: permissions
        ```

    Example (static key):
        ```yaml
        jwt:
          public_key_env: JWT_PUBLIC_KEY
          issuer: my-issuer
          audience: my-agent-api
        ```
    """

    # Key source (one required)
    jwks_url: Optional[str] = None
    public_key_env: Optional[str] = None

    # Validation
    issuer: Optional[str] = None
    audience: Optional[str] = None
    algorithms: List[str] = ["RS256"]
    leeway_seconds: int = 30  # Clock skew tolerance

    # Claim mappings
    claims: Optional[JWTClaimsConfig] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("algorithms")
    @classmethod
    def validate_algorithms(cls, v: List[str]) -> List[str]:
        """Validate algorithms are supported"""
        supported = [
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
            "HS256",
            "HS384",
            "HS512",
        ]
        for alg in v:
            if alg not in supported:
                raise ValidationError(
                    f"Unsupported algorithm: '{alg}'. Supported: {', '.join(supported)}"
                )
        return v

    @field_validator("leeway_seconds")
    @classmethod
    def validate_leeway(cls, v: int) -> int:
        """Validate leeway is reasonable"""
        if v < 0 or v > 300:
            raise ValidationError("leeway_seconds must be 0-300")
        return v


class OAuth2Config(BaseModel):
    """
    OAuth2 token introspection configuration.

    Used for validating opaque tokens by calling the authorization server.

    Example:
        ```yaml
        oauth2:
          introspection_url: https://auth.company.com/oauth/introspect
          client_id_env: AGENT_CLIENT_ID
          client_secret_env: AGENT_CLIENT_SECRET
          required_scopes: [agent:invoke]
        ```

    Note: This is a future feature planned for Phase 2.
    """

    introspection_url: Optional[str] = None
    client_id_env: Optional[str] = None
    client_secret_env: Optional[str] = None
    required_scopes: List[str] = []

    model_config = ConfigDict(extra="allow")


class AuthConfig(BaseModel):
    """
    Authentication and authorization configuration.

    Supports multiple authentication modes:
    - **none**: No authentication (development/trusted networks)
    - **api_key**: API key authentication (single or multi-key)
    - **jwt**: JWT with JWKS support (enterprise SSO)
    - **oauth2**: OAuth2 token introspection (future)

    Example (API Key - simple):
        ```yaml
        auth:
          mode: api_key
        ```

    Example (JWT - enterprise):
        ```yaml
        auth:
          mode: jwt
          jwt:
            jwks_url: https://auth.company.com/.well-known/jwks.json
            issuer: https://auth.company.com/
            audience: my-agent-api
            claims:
              user_id: sub
              roles: permissions
          roles:
            - name: admin
              permissions: [invoke, view_metrics, deploy]
            - name: operator
              permissions: [invoke, view_metrics]
          rate_limits:
            admin: "1000/minute"
            operator: "100/minute"
        ```
    """

    # Auth mode
    mode: str = "api_key"

    # Mode-specific configuration
    api_keys: Optional[ApiKeysConfig] = None
    jwt: Optional[JWTConfig] = None
    oauth2: Optional[OAuth2Config] = None

    # RBAC
    roles: List[RoleConfig] = []

    # Rate limiting by role
    rate_limits: Dict[str, str] = {}

    model_config = ConfigDict(extra="allow")

    @field_validator("mode")
    @classmethod
    def validate_auth_mode_supported(cls, v: str) -> str:
        """Validate auth mode is supported (uses SUPPORTED_AUTH_MODES from common)"""
        if v not in SUPPORTED_AUTH_MODES:
            raise ValidationError(
                f"Unsupported auth mode: '{v}'. Supported modes: {', '.join(SUPPORTED_AUTH_MODES)}"
            )
        return v

    @field_validator("rate_limits")
    @classmethod
    def validate_rate_limit_formats(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate all rate limit strings are properly formatted"""
        for role, limit_str in v.items():
            try:
                parse_rate_limit(limit_str)
            except ValidationError as e:
                raise ValidationError(f"Invalid rate limit for role '{role}': {e.message}")
        return v


# =============================================================================
# OBSERVABILITY CONFIGURATION (Future - Phase 2)
# =============================================================================


class Observability(BaseModel):
    """
    Telemetry and monitoring configuration.

    NOTE: These are optional in MVP. When telemetry is fully integrated,
    these settings control logging and metrics collection.

    Note: log_level field uses constants from common package (LOG_LEVELS)
    as the single source of truth for validation.
    """

    langfuse: Optional[Dict[str, str]] = None
    tracing: bool = True
    log_level: str = "info"  # Validated against LOG_LEVELS from common
    metrics: Dict[str, bool] = {"latency": True, "tokens": True, "cost": True}

    model_config = ConfigDict(extra="allow")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is recognized (uses LOG_LEVELS from common)"""
        if v not in LOG_LEVELS:
            raise ValidationError(
                f"Invalid log level: '{v}'. Valid levels: {', '.join(LOG_LEVELS)}"
            )
        return v


# =============================================================================
# EXPOSE CONFIGURATION
# =============================================================================


class ExposeConfig(BaseModel):
    """
    API exposure and network configuration.

    Controls how the agent runtime exposes APIs (REST, streaming).

    Note: All defaults use RuntimeDefaults from common package
    as the single source of truth.
    """

    rest: bool = True
    streaming: str = RuntimeDefaults.STREAMING
    port: int = RuntimeDefaults.PORT
    host: str = RuntimeDefaults.HOST
    cors: Optional[Dict[str, List[str]]] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("port")
    @classmethod
    def validate_port_range(cls, v: int) -> int:
        """Validate port is in valid range (1-65535)"""
        validate_port(v)
        return v

    @field_validator("streaming")
    @classmethod
    def validate_streaming_mode(cls, v: str) -> str:
        """Validate streaming mode is supported (uses SUPPORTED_STREAMING from common)"""
        if v not in SUPPORTED_STREAMING:
            raise ValidationError(
                f"Unsupported streaming mode: '{v}'. "
                f"Supported modes: {', '.join(SUPPORTED_STREAMING)}"
            )
        return v

    @model_validator(mode="after")
    def validate_at_least_one_exposure(self) -> Self:
        """Validate at least REST or streaming is enabled"""
        if not self.rest and self.streaming == "none":
            raise ValidationError(
                "At least one exposure method must be enabled. "
                "Either set rest=true or streaming to 'sse' or 'websocket'"
            )
        return self


# =============================================================================
# SECRETS CONFIGURATION
# =============================================================================


class SecretDefinition(BaseModel):
    """
    Definition of a secret/environment variable.

    Used to declare what secrets an agent requires at runtime.
    This enables validation before deployment and clear documentation
    of required configuration.

    Example:
        ```yaml
        secrets:
          required:
            - name: OPENAI_API_KEY
              description: "OpenAI API key for LLM calls"
            - name: MY_AGENT_KEY
              description: "API key for agent authentication"
          optional:
            - name: LANGFUSE_SECRET
              description: "Langfuse telemetry"
              default: ""
        ```
    """

    name: str
    description: Optional[str] = None
    default: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate secret name follows environment variable conventions."""
        if not v or not v.strip():
            raise ValidationError("Secret name cannot be empty")
        # Allow uppercase letters, numbers, and underscores
        # Must start with a letter or underscore
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", v):
            raise ValidationError(
                f"Secret name '{v}' must be uppercase with underscores "
                f"(e.g., MY_API_KEY, OPENAI_KEY_1). "
                f"Must start with a letter or underscore."
            )
        return v


class SecretsConfig(BaseModel):
    """
    Configuration for required and optional secrets.

    Secrets declared here are used for:
    - Validation before run/build to ensure required vars are set
    - Documentation of what environment variables the agent needs
    - Auto-loading from .env files with priority resolution

    Example:
        ```yaml
        secrets:
          required:
            - name: OPENAI_API_KEY
              description: "OpenAI API key for LLM calls"
          optional:
            - name: DEBUG_MODE
              description: "Enable debug logging"
              default: "false"
        ```
    """

    required: List[SecretDefinition] = []
    optional: List[SecretDefinition] = []

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_no_duplicate_names(self) -> Self:
        """Ensure no duplicate secret names across required and optional."""
        all_names = [s.name for s in self.required] + [s.name for s in self.optional]
        seen = set()
        duplicates = []
        for name in all_names:
            if name in seen:
                duplicates.append(name)
            seen.add(name)

        if duplicates:
            raise ValidationError(
                f"Duplicate secret names found: {', '.join(duplicates)}. "
                f"Each secret must have a unique name."
            )
        return self


# =============================================================================
# METADATA
# =============================================================================


class Metadata(BaseModel):
    """
    Optional descriptive metadata about the agent.

    Used for documentation and organization purposes.
    """

    maintainer: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = []

    model_config = ConfigDict(extra="allow")


# =============================================================================
# STREAMING CONFIGURATION
# =============================================================================


class StreamingEventsConfig(BaseModel):
    """
    Configuration for event emission using allow-list approach.

    Controls which events are emitted by the runtime. Uses an allow-list model
    where you specify which events you want enabled.

    Configuration options for `allowed`:
    - `null` / omitted: All events enabled (default)
    - Preset string: `"chat"`, `"debug"`, `"minimal"`, `"all"`
    - Explicit list: `["token", "step", "custom:fraud_check"]`

    Presets:
    - `"minimal"`: Only mandatory lifecycle events (started, complete, error, cancelled)
    - `"chat"`: token, step, heartbeat (optimized for chat UIs)
    - `"debug"`: All events including custom (for development)
    - `"all"`: Same as debug, all events enabled

    Mandatory events (always emitted regardless of config):
    - started, complete, error, cancelled

    Configurable events:
    - token: LLM token streaming
    - step: Node/step completion events
    - progress: Progress percentage updates
    - checkpoint: Intermediate state snapshots
    - heartbeat: Keep-alive events

    Custom events:
    - `"custom"`: Allow all custom events
    - `"custom:name"`: Allow specific custom event

    Example:
        ```yaml
        streaming:
          events:
            allowed: chat  # Use preset
            heartbeat_interval: 15
            max_run_duration: 3600
        ```

        ```yaml
        streaming:
          events:
            allowed:  # Explicit list
              - token
              - step
              - custom:fraud_check
        ```
    """

    allowed: Optional[Union[List[str], str]] = None
    """
    Which events to allow. Can be:
    - null: All events allowed (default)
    - Preset string: "chat", "debug", "minimal", "all"
    - List of event types: ["token", "step", "custom:fraud_check"]
    """

    heartbeat_interval: int = 15
    """Heartbeat interval in seconds."""

    max_run_duration: int = 3600
    """Maximum run duration in seconds before timeout."""

    model_config = ConfigDict(extra="allow")

    @field_validator("allowed")
    @classmethod
    def validate_allowed(cls, v: Optional[Union[List[str], str]]) -> Optional[Union[List[str], str]]:
        """Validate allowed events configuration."""
        # Constants defined inline to avoid Pydantic private attribute issues
        valid_presets = {"minimal", "chat", "debug", "all"}
        valid_event_types = {"token", "step", "progress", "checkpoint", "heartbeat"}
        mandatory_events = {"started", "complete", "error", "cancelled"}

        if v is None:
            return v

        if isinstance(v, str):
            # Validate preset name
            if v not in valid_presets:
                presets_str = ", ".join(sorted(valid_presets))
                raise ValidationError(
                    f"Unknown events preset: '{v}'. Valid presets: {presets_str}"
                )
            return v

        if isinstance(v, list):
            for item in v:
                if not isinstance(item, str):
                    raise ValidationError(f"Event type must be a string, got {type(item).__name__}")

                # Check for custom event pattern
                if item.startswith("custom:"):
                    custom_name = item[7:]
                    if not custom_name:
                        raise ValidationError("Custom event name cannot be empty in 'custom:'")
                    # Custom event names should be valid identifiers
                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", custom_name):
                        raise ValidationError(
                            f"Invalid custom event name: '{custom_name}'. "
                            "Must be a valid identifier (letters, digits, underscores)."
                        )
                    continue

                # "custom" wildcard is valid
                if item == "custom":
                    continue

                # Check if it's a valid built-in event type
                if item not in valid_event_types:
                    # Also allow mandatory events in list (they're just ignored)
                    if item not in mandatory_events:
                        valid_types_str = ", ".join(sorted(valid_event_types | {"custom", "custom:<name>"}))
                        raise ValidationError(
                            f"Unknown event type: '{item}'. Valid types: {valid_types_str}"
                        )

            return v

        raise ValidationError("allowed must be null, a preset string, or a list of event types")

    @field_validator("heartbeat_interval")
    @classmethod
    def validate_heartbeat_interval(cls, v: int) -> int:
        """Validate heartbeat interval is reasonable."""
        if v < 1 or v > 300:
            raise ValidationError("heartbeat_interval must be between 1 and 300 seconds")
        return v

    @field_validator("max_run_duration")
    @classmethod
    def validate_max_run_duration(cls, v: int) -> int:
        """Validate max run duration is reasonable."""
        if v < 1 or v > 86400:  # Max 24 hours
            raise ValidationError("max_run_duration must be between 1 and 86400 seconds")
        return v


class StreamingConnectionConfig(BaseModel):
    """
    SSE connection settings.

    Example:
        ```yaml
        streaming:
          connection:
            default_timeout: 300
            max_subscribers_per_run: 100
        ```
    """

    default_timeout: int = 300
    """Default SSE connection timeout in seconds."""

    max_subscribers_per_run: int = 100
    """Maximum concurrent subscribers per run."""

    model_config = ConfigDict(extra="allow")

    @field_validator("default_timeout")
    @classmethod
    def validate_default_timeout(cls, v: int) -> int:
        """Validate timeout is reasonable."""
        if v < 1 or v > 3600:
            raise ValidationError("default_timeout must be between 1 and 3600 seconds")
        return v

    @field_validator("max_subscribers_per_run")
    @classmethod
    def validate_max_subscribers(cls, v: int) -> int:
        """Validate max subscribers is reasonable."""
        if v < 1 or v > 1000:
            raise ValidationError("max_subscribers_per_run must be between 1 and 1000")
        return v


class StreamingIdGenerator(BaseModel):
    """
    Run ID generator configuration.

    Supports UUID (default) or custom generator function.

    Example:
        ```yaml
        streaming:
          id_generator:
            type: custom
            handler: myapp.ids:generate_run_id
        ```
    """

    type: str = "uuid"
    """Generator type: 'uuid' or 'custom'."""

    handler: Optional[str] = None
    """Custom generator function path (for type='custom')."""

    model_config = ConfigDict(extra="allow")

    @field_validator("type")
    @classmethod
    def validate_generator_type(cls, v: str) -> str:
        """Validate generator type."""
        valid_types = ["uuid", "custom"]
        if v not in valid_types:
            raise ValidationError(f"id_generator type must be one of: {', '.join(valid_types)}")
        return v

    @model_validator(mode="after")
    def validate_custom_handler(self) -> Self:
        """Ensure custom type has handler."""
        if self.type == "custom" and not self.handler:
            raise ValidationError("Custom id_generator requires 'handler' field")
        return self


class RedisStreamingConfig(BaseModel):
    """
    Redis backend configuration for streaming.

    Example:
        ```yaml
        streaming:
          backend: redis
          redis:
            url: ${REDIS_URL}
            stream_ttl_seconds: 3600
            max_events_per_run: 1000
            connection_pool_size: 10
        ```
    """

    url: str = "${REDIS_URL}"
    """Redis connection URL (supports env var substitution)."""

    stream_ttl_seconds: int = 3600
    """Event retention time in seconds."""

    max_events_per_run: int = 1000
    """Maximum events to retain per run."""

    connection_pool_size: int = 10
    """Redis connection pool size."""

    model_config = ConfigDict(extra="allow")

    @field_validator("stream_ttl_seconds")
    @classmethod
    def validate_stream_ttl(cls, v: int) -> int:
        """Validate TTL is reasonable."""
        if v < 60 or v > 604800:  # 1 minute to 1 week
            raise ValidationError("stream_ttl_seconds must be between 60 and 604800")
        return v

    @field_validator("max_events_per_run")
    @classmethod
    def validate_max_events(cls, v: int) -> int:
        """Validate max events is reasonable."""
        if v < 10 or v > 100000:
            raise ValidationError("max_events_per_run must be between 10 and 100000")
        return v


class StreamingConfig(BaseModel):
    """
    Complete streaming configuration.

    Controls async runs, backend selection, and event settings.

    Example:
        ```yaml
        streaming:
          async_runs: true
          backend: redis
          redis:
            url: ${REDIS_URL}
          allow_client_ids: true
          events:
            heartbeat_interval: 15
          connection:
            default_timeout: 300
        ```
    """

    async_runs: bool = True
    """Enable async runs (Pattern B: POST /runs + GET /runs/{id}/events)."""

    backend: str = "memory"
    """Backend type: 'memory' or 'redis'."""

    redis: Optional[RedisStreamingConfig] = None
    """Redis-specific configuration (required if backend='redis')."""

    id_generator: Optional[StreamingIdGenerator] = None
    """Run ID generator configuration."""

    allow_client_ids: bool = True
    """Allow client-provided run IDs."""

    events: Optional[StreamingEventsConfig] = None
    """Event emission configuration."""

    connection: Optional[StreamingConnectionConfig] = None
    """Connection settings."""

    model_config = ConfigDict(extra="allow")

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, v: str) -> str:
        """Validate backend type."""
        valid_backends = ["memory", "redis"]
        if v not in valid_backends:
            raise ValidationError(f"backend must be one of: {', '.join(valid_backends)}")
        return v

    @model_validator(mode="after")
    def validate_redis_config(self) -> Self:
        """Ensure redis config is provided when backend is redis."""
        if self.backend == "redis" and not self.redis:
            # Create default redis config if not provided
            object.__setattr__(self, "redis", RedisStreamingConfig())
        return self


# =============================================================================
# BUILD CONFIGURATION
# =============================================================================


class BuildIncludeConfig(BaseModel):
    """
    Files and directories to include in Docker build.

    These are added to the auto-detected entrypoint module.
    Use this to include additional code, data files, or configuration
    that your agent needs at runtime.

    Example:
        ```yaml
        build:
          include:
            directories:
              - utils
              - models
            files:
              - config.yaml
              - constants.py
            patterns:
              - "data/*.json"
        ```
    """

    directories: List[str] = []
    """Additional directories to copy (e.g., ["utils", "models"])"""

    files: List[str] = []
    """Additional files to copy (e.g., ["config.yaml", "constants.py"])"""

    patterns: List[str] = []
    """Glob patterns to match files (e.g., ["*.json", "data/**"])"""

    model_config = ConfigDict(extra="allow")

    @field_validator("directories", "files", "patterns")
    @classmethod
    def validate_non_empty_strings(cls, v: List[str]) -> List[str]:
        """Validate that list items are non-empty strings."""
        for item in v:
            if not item or not item.strip():
                raise ValidationError("Build include items cannot be empty strings")
        return v


class BuildConfig(BaseModel):
    """
    Build configuration for Docker image creation.

    Controls what gets copied into the Docker image beyond
    the auto-detected entrypoint module. Use this for:
    - Including additional code directories
    - Including data files or configuration
    - Excluding test files or development artifacts
    - Auto-detecting local imports

    Example:
        ```yaml
        build:
          include:
            directories:
              - utils
              - models
            files:
              - config.yaml
          exclude:
            - "tests/"
            - "**/__pycache__"
          auto_detect_imports: false
        ```
    """

    include: Optional[BuildIncludeConfig] = None
    """Additional files/directories to include"""

    exclude: List[str] = []
    """Patterns to exclude (e.g., ["tests/", "**/__pycache__"])"""

    auto_detect_imports: bool = False
    """If True, parse Python files to detect and include local imports"""

    model_config = ConfigDict(extra="allow")

    @field_validator("exclude")
    @classmethod
    def validate_exclude_patterns(cls, v: List[str]) -> List[str]:
        """Validate that exclude patterns are non-empty strings."""
        for pattern in v:
            if not pattern or not pattern.strip():
                raise ValidationError("Exclude patterns cannot be empty strings")
        return v


# =============================================================================
# ROOT DOCKSPEC MODEL
# =============================================================================


class DockSpec(BaseModel):
    """
    Root model for Dockfile v1.0 specification.

    This is the main entry point for validating Dockfile configurations.
    All services use this model to ensure consistent validation.

    Design:
    - Accepts unknown fields (extra="allow") for future extensibility
    - MVP fields are required/validated, future fields are accepted but not validated
    - When new services are ready, corresponding models are added and validated

    Usage:
        # SDK passes parsed YAML dict to schema
        data = yaml.safe_load(file_content)
        spec = DockSpec.model_validate(data)

        # Access validated fields
        agent_name = spec.agent.name
        framework = spec.agent.framework
    """

    version: Literal["1.0"]
    agent: AgentConfig
    io_schema: IOSchema
    arguments: Dict[str, Any] = {}
    policies: Optional[Policies] = None
    auth: Optional[AuthConfig] = None
    observability: Optional[Observability] = None
    expose: ExposeConfig
    metadata: Optional[Metadata] = None
    secrets: Optional[SecretsConfig] = None
    build: Optional[BuildConfig] = None
    streaming: Optional[StreamingConfig] = None

    # Allow unknown fields for future expansion (Phase 2+)
    # When new services are built, add their models above and make them optional
    model_config = ConfigDict(extra="allow")

    @field_validator("version")
    @classmethod
    def validate_version_supported(cls, v: str) -> str:
        """Validate Dockfile version is supported"""
        if v not in SUPPORTED_DOCKFILE_VERSIONS:
            raise ValidationError(
                f"Unsupported Dockfile version: '{v}'. "
                f"Supported versions: {', '.join(SUPPORTED_DOCKFILE_VERSIONS)}"
            )
        return v
