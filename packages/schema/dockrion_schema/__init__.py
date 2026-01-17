"""
dockrion Schema Package

Type-safe validation layer for Dockfile configurations.

This package provides Pydantic models for validating and working with
Dockfile specifications. It's the foundation for consistent validation
across all dockrion services.

Design Principles:
- Pure validation: Receives dicts, validates structure, returns typed objects
- No file I/O: File reading/writing is SDK's responsibility
- Extensible: Accepts unknown fields for future expansion
- Security-first: Critical validations prevent code injection

Usage:
    from dockrion_schema import DockSpec, ValidationError

    # SDK passes parsed YAML dict to schema for validation
    data = yaml.safe_load(file_content)

    try:
        spec = DockSpec.model_validate(data)
        print(f"Agent: {spec.agent.name}")
        print(f"Framework: {spec.agent.framework}")
    except ValidationError as e:
        print(f"Validation failed: {e.message}")

Public API:
    # Models
    - DockSpec: Root model for Dockfile v1.0
    - AgentConfig: Agent metadata and entrypoint
    - IOSchema, IOSubSchema: Input/output schema definitions
    - ExposeConfig: API exposure configuration
    - Metadata: Optional descriptive metadata
    - Policies: Security policies (optional)
    - AuthConfig: Authentication configuration (optional)
    - Observability: Telemetry configuration (optional)

    # Utilities
    - to_dict(): Convert DockSpec to dict
    - to_yaml_string(): Serialize DockSpec to YAML string
    - from_dict(): Create DockSpec from dict
    - generate_json_schema(): Generate JSON Schema for IDE support

    # Errors
    - ValidationError: Validation error (re-exported from common)
"""

# Models - Core (MVP)
# Errors (re-exported from common)
from dockrion_common import ValidationError

# Models - Advanced (Future - Phase 2)
from .dockfile_v1 import (
    AgentConfig,
    ApiKeysConfig,
    AuthConfig,
    DockSpec,
    ExposeConfig,
    IOSchema,
    IOSubSchema,
    Metadata,
    Observability,
    Policies,
    RedisStreamingConfig,
    RoleConfig,
    SafetyPolicy,
    SecretDefinition,
    SecretsConfig,
    StreamingConfig,
    StreamingConnectionConfig,
    StreamingEventsConfig,
    StreamingIdGenerator,
    ToolPolicy,
)

# JSON Schema generation
from .json_schema import (
    generate_json_schema,
    get_schema_version,
    write_json_schema,
)

# Serialization utilities
from .serialization import (
    from_dict,
    to_dict,
    to_yaml_string,
)

__version__ = "0.1.0"

__all__ = [
    # Core Models (MVP)
    "DockSpec",
    "AgentConfig",
    "IOSchema",
    "IOSubSchema",
    "ExposeConfig",
    "Metadata",
    "SecretDefinition",
    "SecretsConfig",
    # Advanced Models (Future)
    "Policies",
    "ToolPolicy",
    "SafetyPolicy",
    "AuthConfig",
    "RoleConfig",
    "ApiKeysConfig",
    "Observability",
    # Streaming Models
    "StreamingConfig",
    "StreamingEventsConfig",
    "StreamingConnectionConfig",
    "StreamingIdGenerator",
    "RedisStreamingConfig",
    # Serialization
    "to_dict",
    "to_yaml_string",
    "from_dict",
    # JSON Schema
    "generate_json_schema",
    "write_json_schema",
    "get_schema_version",
    # Errors
    "ValidationError",
]
