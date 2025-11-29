# Dockrion Schema Package

Type-safe validation layer for Dockfile configurations.

## Overview

The `dockrion-schema` package provides Pydantic models for validating and working with Dockfile specifications. It's the foundation for consistent validation across all Dockrion services.

**Key Features:**
- 🔒 Type-safe validation with Pydantic v2
- 🚀 Fast validation (<100ms for typical Dockfiles)
- 🛡️ Security-first: prevents code injection and validates critical fields
- 🔄 Extensible: accepts unknown fields for future compatibility
- 📝 Pure validation: no file I/O, testable without mocking

## Installation

```bash
# Install from local repository
pip install -e packages/schema

# With development dependencies (for testing)
pip install -e "packages/schema[dev]"
```

## Architecture Position

```
Schema Package (foundation layer)
    ↓ depends on
Common Package (utilities)

Used by → CLI, SDK, Builder, Controller, Runtime, Dashboard
```

**Critical Boundary:** Schema validates data structures. File I/O, YAML parsing, and environment variable expansion belong in SDK/CLI.

## Design Principles

### 1. Pure Validation
Schema receives dicts, validates structure, returns typed objects. **NO file I/O.**

```python
# ✅ Schema's job: Validate dict
spec = DockSpec.model_validate(data)

# ❌ NOT schema's job: Read files
# This belongs in SDK
with open("Dockfile.yaml") as f:
    data = yaml.safe_load(f)
```

### 2. Single Source of Truth (Constants from Common)
All supported values (frameworks, providers, auth modes, etc.) are defined in `dockrion-common` and imported by schema for validation.

```python
# Schema imports constants from common
from dockrion_common import (
    SUPPORTED_FRAMEWORKS,
    SUPPORTED_PROVIDERS,
    SUPPORTED_AUTH_MODES,
    LOG_LEVELS,
    SUPPORTED_STREAMING
)

# Validation uses these constants
@field_validator("framework")
def validate_framework(cls, v: str) -> str:
    if v not in SUPPORTED_FRAMEWORKS:
        raise ValidationError(f"Unsupported framework: {v}")
    return v
```

**Benefits:**
- No duplication of constants across packages
- Easy to add new supported values (just update `common/constants.py`)
- Consistent validation rules across all Dockrion services

### 3. Extensibility
Models accept unknown fields using `ConfigDict(extra="allow")` for future expansion.

```python
# Future fields don't break existing deployments
data = {
    "version": "1.0",
    "agent": {...},
    "future_feature": {...}  # ✅ Accepted but not validated
}
```

### 4. Security First
Critical validations prevent security issues:
- Entrypoint injection prevention
- Port range validation
- Framework/provider whitelisting (using constants from common)

## Quick Start

### Basic Usage

```python
from dockrion_schema import DockSpec, ValidationError

# SDK passes parsed YAML dict to schema
data = {
    "version": "1.0",
    "agent": {
        "name": "invoice-copilot",
        "entrypoint": "app.main:build_graph",
        "framework": "langgraph"
    },
    "io_schema": {},
    "expose": {
        "port": 8080
    }
}

try:
    # Validate configuration
    spec = DockSpec.model_validate(data)
    
    # Access validated fields (type-safe)
    print(f"Agent: {spec.agent.name}")
    print(f"Framework: {spec.agent.framework}")
    print(f"Port: {spec.expose.port}")
    
except ValidationError as e:
    print(f"Validation failed: {e.message}")
```

### Serialization

```python
from dockrion_schema import to_dict, to_yaml_string, from_dict

# Convert spec to dict
spec_dict = to_dict(spec)

# Convert spec to YAML string
yaml_str = to_yaml_string(spec)

# SDK would then write to file:
# with open("Dockfile.yaml", "w") as f:
#     f.write(yaml_str)

# Create spec from dict
spec = from_dict(data)
```

### JSON Schema Generation

```python
from dockrion_schema import generate_json_schema, write_json_schema

# Get JSON Schema as dict
schema = generate_json_schema()

# Write to file for IDE support
write_json_schema("dockfile_v1_schema.json")

# Then add to your Dockfile.yaml:
# # yaml-language-server: $schema=./dockfile_v1_schema.json
# version: "1.0"
# ...
```

## API Reference

### Core Models (MVP)

#### DockSpec
Root model for Dockfile v1.0 specification.

```python
class DockSpec(BaseModel):
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
```

#### AgentConfig
Agent metadata and code location.

```python
class AgentConfig(BaseModel):
    name: str  # lowercase, alphanumeric, hyphens only
    description: Optional[str] = None
    entrypoint: str  # format: 'module.path:callable'
    framework: Literal["langgraph", "langchain"]
```

**Validators:**
- `name`: Must be lowercase alphanumeric with hyphens
- `entrypoint`: Must be valid `module:callable` format, prevents injection
- `framework`: Must be in `SUPPORTED_FRAMEWORKS`

#### IOSchema
Input/output schema for agent invocation.

```python
class IOSchema(BaseModel):
    input: Optional[IOSubSchema] = None
    output: Optional[IOSubSchema] = None

class IOSubSchema(BaseModel):
    type: Literal["object"] = "object"
    properties: Dict[str, dict] = {}
    required: List[str] = []
```

#### ExposeConfig
API exposure and network configuration.

```python
class ExposeConfig(BaseModel):
    rest: bool = True
    streaming: Literal["sse", "websocket", "none"] = "sse"
    port: int = 8080  # 1-65535
    host: str = "0.0.0.0"
    cors: Optional[Dict[str, List[str]]] = None
```

**Validators:**
- `port`: Must be between 1 and 65535
- `streaming`: Must be in `SUPPORTED_STREAMING`
- Model validator: At least REST or streaming must be enabled

#### Metadata
Optional descriptive metadata.

```python
class Metadata(BaseModel):
    maintainer: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = []
```

### Advanced Models (Future - Phase 2)

These models are included for future compatibility but are optional in MVP:

#### ModelConfig
LLM provider and model settings.

```python
class ModelConfig(BaseModel):
    provider: Literal["openai", "azure", "anthropic", "google", "ollama", "custom"]
    name: str
    temperature: Optional[float] = None  # 0-2
    max_tokens: Optional[int] = None  # positive
    endpoint: Optional[str] = None
    extra: Dict[str, Any] = {}
```

#### Policies
Security and safety policies.

```python
class Policies(BaseModel):
    tools: Optional[ToolPolicy] = None
    safety: Optional[SafetyPolicy] = None

class ToolPolicy(BaseModel):
    allowed: List[str] = []
    deny_by_default: bool = True

class SafetyPolicy(BaseModel):
    redact_patterns: List[str] = []
    max_output_chars: Optional[int] = None  # positive
    block_prompt_injection: bool = True
    halt_on_violation: bool = False
```

#### AuthConfig
Authentication and authorization configuration.

```python
class AuthConfig(BaseModel):
    mode: Literal["jwt", "api_key", "oauth2"] = "api_key"
    api_keys: Optional[ApiKeysConfig] = None
    roles: List[RoleConfig] = []
    rate_limits: Dict[str, str] = {}  # e.g., {"admin": "1000/m"}
```

**Validators:**
- `mode`: Must be in `SUPPORTED_AUTH_MODES`
- `rate_limits`: Each value must be valid format (e.g., "1000/m")
- `roles[].permissions`: Each permission must be in `PERMISSIONS`

#### Observability
Telemetry and monitoring configuration.

```python
class Observability(BaseModel):
    langfuse: Optional[Dict[str, str]] = None
    tracing: bool = True
    log_level: Literal["debug", "info", "warn", "error"] = "info"
    metrics: Dict[str, bool] = {"latency": True, "tokens": True, "cost": True}
```

### Utility Functions

#### to_dict(spec, exclude_none=True)
Convert DockSpec to plain Python dictionary.

```python
data = to_dict(spec)
# Returns: {"version": "1.0", "agent": {...}, ...}
```

#### to_yaml_string(spec, exclude_none=True)
Serialize DockSpec to YAML string (NOT write to file).

```python
yaml_str = to_yaml_string(spec)
# Returns: "version: '1.0'\nagent:\n  name: test\n..."
```

#### from_dict(data)
Create DockSpec from dictionary (convenience wrapper).

```python
spec = from_dict(data)
# Equivalent to: DockSpec.model_validate(data)
```

#### generate_json_schema()
Generate JSON Schema v7 for IDE support.

```python
schema = generate_json_schema()
# Returns: {"$schema": "...", "properties": {...}, ...}
```

#### write_json_schema(output_path)
Write JSON Schema to file for editor plugins.

```python
write_json_schema("dockfile_v1_schema.json")
# Creates file that IDEs can use for autocomplete
```

## Integration Examples

### How SDK Uses Schema

```python
# packages/sdk/dockrion_sdk/validate.py
from dockrion_schema import DockSpec, ValidationError
import yaml

def validate_dockfile(path: str) -> DockSpec:
    """SDK handles file I/O, schema validates"""
    # Step 1: SDK reads file
    with open(path) as f:
        content = f.read()
    
    # Step 2: SDK parses YAML
    data = yaml.safe_load(content)
    
    # Step 3: SDK expands environment variables
    data = expand_env_vars(data)
    
    # Step 4: Schema validates
    return DockSpec.model_validate(data)
```

### How CLI Uses Schema

```python
# packages/cli/dockrion_cli/validate_cmd.py
from dockrion_sdk import validate_dockfile
from dockrion_schema import ValidationError
import typer

@app.command()
def validate(path: str = "Dockfile.yaml"):
    try:
        spec = validate_dockfile(path)  # SDK + Schema
        typer.echo("✅ Dockfile valid")
        typer.echo(f"Agent: {spec.agent.name}")
        typer.echo(f"Framework: {spec.agent.framework}")
    except ValidationError as e:
        typer.echo(f"❌ {e.message}", err=True)
        raise typer.Exit(1)
```

### How Runtime Uses Schema

```python
# Generated runtime.py
from dockrion_schema import DockSpec

# SDK embeds validated spec in generated runtime
SPEC = {
    "version": "1.0",
    "agent": {"name": "invoice-copilot", ...},
    ...
}

# Runtime uses spec for configuration
@app.post("/invoke")
async def invoke(request: Request):
    # Validate input against io_schema
    input_schema = SPEC["io_schema"]["input"]
    # ... validate request.json() against input_schema
```

## Testing

```bash
# Run all tests
cd packages/schema
pytest tests/

# Run with coverage
pytest tests/ --cov=dockrion_schema --cov-report=html

# Run specific test file
pytest tests/test_models.py -v

# Run specific test
pytest tests/test_models.py::TestAgentConfig::test_valid_agent_config -v
```

## Error Handling

Schema uses `ValidationError` from `dockrion-common` for all validation errors:

```python
from dockrion_schema import ValidationError

try:
    spec = DockSpec.model_validate(data)
except ValidationError as e:
    print(f"Error: {e.message}")
    print(f"Code: {e.code}")
    
    # Format for user display
    error_dict = e.to_dict()
    # {"error": "ValidationError", "code": "VALIDATION_ERROR", "message": "..."}
```

## Common Validation Errors

### Invalid Agent Name
```python
# ❌ Uppercase not allowed
{"agent": {"name": "Invoice-Copilot", ...}}
# Error: Agent name must be lowercase alphanumeric with hyphens only

# ✅ Correct format
{"agent": {"name": "invoice-copilot", ...}}
```

### Invalid Entrypoint
```python
# ❌ Missing colon
{"agent": {"entrypoint": "app.main", ...}}
# Error: Entrypoint must be in format 'module:callable'

# ✅ Correct format
{"agent": {"entrypoint": "app.main:build_graph", ...}}
```

### Invalid Port
```python
# ❌ Out of range
{"expose": {"port": 70000}}
# Error: Port must be between 1 and 65535

# ✅ Valid port
{"expose": {"port": 8080}}
```

### No Exposure Method
```python
# ❌ Nothing exposed
{"expose": {"rest": false, "streaming": "none", "port": 8080}}
# Error: At least one exposure method must be enabled

# ✅ REST or streaming enabled
{"expose": {"rest": true, "streaming": "none", "port": 8080}}
```

## Extensibility Strategy

### Adding Future Fields

Models use `ConfigDict(extra="allow")` to accept unknown fields:

```python
# MVP Dockfile
{
    "version": "1.0",
    "agent": {...},
    "expose": {...}
}

# Future Dockfile (when services ready)
{
    "version": "1.0",
    "agent": {...},
    "expose": {...},
    "custom_section": {...}  # ✅ Accepted but not validated yet
}
```

When new services are built:
1. Add corresponding Pydantic model to `dockfile_v1.py`
2. Make field optional in `DockSpec`
3. Add validators as needed
4. Update documentation

### Version Migration

When Dockfile v2 is needed:
1. Create `dockfile_v2.py` with new models
2. Keep `dockfile_v1.py` for backward compatibility
3. SDK routes based on `version` field
4. Both versions coexist without breaking changes

## Dependencies

### Required
- `pydantic>=2.5` - Core validation framework
- `dockrion-common` - Validation utilities and constants

### Optional (dev)
- `pyyaml>=6.0` - For YAML serialization (`to_yaml_string()`)
- `pytest>=7.4` - Testing framework
- `pytest-cov>=4.1` - Coverage reporting

## Contributing

When adding new validators or models:

1. **Add field validator:**
```python
@field_validator("new_field")
@classmethod
def validate_new_field(cls, v: str) -> str:
    # Validation logic
    return v
```

2. **Add model validator:**
```python
@model_validator(mode="after")
def validate_cross_field(self) -> Self:
    # Cross-field validation
    return self
```

3. **Add tests:**
```python
def test_new_field_validation():
    """Test new field validation"""
    # Test valid cases
    # Test invalid cases
```

4. **Update documentation:**
- Add to API Reference section
- Add usage example
- Document validation rules

## Design Decisions

### Why No File I/O?
- **Testability**: Pure functions easy to test without file mocking
- **Flexibility**: Can validate dicts from any source (files, APIs, databases)
- **Separation**: Clear boundary between I/O (SDK) and validation (Schema)

### Why Accept Unknown Fields?
- **Future compatibility**: New fields don't break existing deployments
- **Gradual rollout**: Add models when services are ready
- **Extensibility**: Users can experiment with custom fields

### Why Import from Common?
- **DRY principle**: Don't duplicate validation logic
- **Consistency**: Same constants and validators everywhere
- **Maintainability**: Fix bugs in one place

## Troubleshooting

### Import Error: dockrion-common not found
```bash
# Install common package first
pip install -e packages/common-py
pip install -e packages/schema
```

### PyYAML not found when using to_yaml_string()
```bash
# Install with dev dependencies
pip install -e "packages/schema[dev]"
```

### Validation errors unclear
```python
# Use ValidationError.to_dict() for structured error info
try:
    spec = DockSpec.model_validate(data)
except ValidationError as e:
    error_info = e.to_dict()
    print(f"Error: {error_info['error']}")
    print(f"Code: {error_info['code']}")
    print(f"Message: {error_info['message']}")
```

## Support

- **Documentation**: See `docs/SCHEMA_PACKAGE_SPEC.md`
- **Examples**: Check `tests/` directory for usage examples
- **Issues**: GitHub Issues on Dockrion repository

## License

See repository LICENSE file.

