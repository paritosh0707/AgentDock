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

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional, Literal, Dict, List, Any
from typing_extensions import Self

# Import validation utilities and constants from common package
from dockrion_common import (
    ValidationError,
    SUPPORTED_FRAMEWORKS,
    SUPPORTED_PROVIDERS,
    SUPPORTED_AUTH_MODES,
    SUPPORTED_STREAMING,
    LOG_LEVELS,
    PERMISSIONS,
    SUPPORTED_DOCKFILE_VERSIONS,
    validate_entrypoint,
    validate_agent_name,
    validate_port,
    parse_rate_limit,
)


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
                SUPPORTED_TYPES = ["object", "string", "number", "integer", "boolean", "array", "null"]
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
    """
    input: Optional[IOSubSchema] = None
    output: Optional[IOSubSchema] = None
    
    model_config = ConfigDict(extra="allow")


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

class AgentConfig(BaseModel):
    """
    Agent metadata and code location.
    
    Specifies the agent's entrypoint, framework, and descriptive information.
    
    Note: framework field uses constants from common package (SUPPORTED_FRAMEWORKS)
    as the single source of truth for validation.
    """
    name: str
    description: Optional[str] = None
    entrypoint: str
    framework: Literal[tuple(SUPPORTED_FRAMEWORKS)]  # Validated against SUPPORTED_FRAMEWORKS from common
    # framework: str  # Validated against SUPPORTED_FRAMEWORKS from common
    
    model_config = ConfigDict(extra="allow")
    
    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate agent name format (lowercase, alphanumeric, hyphens)"""
        validate_agent_name(v)
        return v
    
    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint_format(cls, v: str) -> str:
        """
        Validate entrypoint format and prevent code injection.
        
        Format: 'module.path:callable'
        Prevents: os.system:eval, ../../../etc/passwd:read
        """
        validate_entrypoint(v)
        return v
    
    @field_validator("framework")
    @classmethod
    def validate_framework_supported(cls, v: str) -> str:
        """Validate framework is supported (uses SUPPORTED_FRAMEWORKS from common)"""
        if v not in SUPPORTED_FRAMEWORKS:
            raise ValidationError(
                f"Unsupported framework: '{v}'. "
                f"Supported frameworks: {', '.join(SUPPORTED_FRAMEWORKS)}"
            )
        return v


# =============================================================================
# MODEL CONFIGURATION (Future - Phase 2)
# =============================================================================

class ModelConfig(BaseModel):
    """
    LLM provider and model settings.
    
    NOTE: This is included for future compatibility but not required in MVP.
    Runtime can use this to configure LLM clients.
    
    Note: provider field uses constants from common package (SUPPORTED_PROVIDERS)
    as the single source of truth for validation.
    """
    provider: str  # Validated against SUPPORTED_PROVIDERS from common
    name: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    endpoint: Optional[str] = None
    extra: Dict[str, Any] = {}
    
    model_config = ConfigDict(extra="allow")
    
    @field_validator("provider")
    @classmethod
    def validate_provider_supported(cls, v: str) -> str:
        """Validate provider is supported (uses SUPPORTED_PROVIDERS from common)"""
        if v not in SUPPORTED_PROVIDERS:
            raise ValidationError(
                f"Unsupported provider: '{v}'. "
                f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
            )
        return v
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature_range(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature is in valid range [0, 2]"""
        if v is not None and (v < 0 or v > 2):
            raise ValidationError(f"Temperature must be between 0 and 2. Got: {v}")
        return v
    
    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens_positive(cls, v: Optional[int]) -> Optional[int]:
        """Validate max_tokens is positive"""
        if v is not None and v <= 0:
            raise ValidationError(f"max_tokens must be positive. Got: {v}")
        return v


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
# AUTH CONFIGURATION (Future - Phase 2)
# =============================================================================

class RoleConfig(BaseModel):
    """
    Role-based access control configuration.
    
    NOTE: Auth enforcement happens in auth service or runtime.
    Schema validates configuration structure.
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
                    f"Unknown permission: '{perm}'. "
                    f"Valid permissions: {', '.join(PERMISSIONS)}"
                )
        return v


class ApiKeysConfig(BaseModel):
    """API key authentication configuration"""
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


class AuthConfig(BaseModel):
    """
    Authentication and authorization configuration.
    
    NOTE: These are optional in MVP. When auth service is ready,
    these will be enforced.
    
    Note: mode field uses constants from common package (SUPPORTED_AUTH_MODES)
    as the single source of truth for validation.
    """
    mode: str = "api_key"  # Validated against SUPPORTED_AUTH_MODES from common
    api_keys: Optional[ApiKeysConfig] = None
    roles: List[RoleConfig] = []
    rate_limits: Dict[str, str] = {}
    
    model_config = ConfigDict(extra="allow")
    
    @field_validator("mode")
    @classmethod
    def validate_auth_mode_supported(cls, v: str) -> str:
        """Validate auth mode is supported (uses SUPPORTED_AUTH_MODES from common)"""
        if v not in SUPPORTED_AUTH_MODES:
            raise ValidationError(
                f"Unsupported auth mode: '{v}'. "
                f"Supported modes: {', '.join(SUPPORTED_AUTH_MODES)}"
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
                raise ValidationError(
                    f"Invalid rate limit for role '{role}': {e.message}"
                )
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
                f"Invalid log level: '{v}'. "
                f"Valid levels: {', '.join(LOG_LEVELS)}"
            )
        return v


# =============================================================================
# EXPOSE CONFIGURATION
# =============================================================================

class ExposeConfig(BaseModel):
    """
    API exposure and network configuration.
    
    Controls how the agent runtime exposes APIs (REST, streaming).
    
    Note: streaming field uses constants from common package (SUPPORTED_STREAMING)
    as the single source of truth for validation.
    """
    rest: bool = True
    streaming: str = "sse"  # Validated against SUPPORTED_STREAMING from common
    port: int = 8080
    host: str = "0.0.0.0"
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
    model: Optional[ModelConfig] = None
    io_schema: IOSchema
    arguments: Dict[str, Any] = {}
    policies: Optional[Policies] = None
    auth: Optional[AuthConfig] = None
    observability: Optional[Observability] = None
    expose: ExposeConfig
    metadata: Optional[Metadata] = None
    
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
