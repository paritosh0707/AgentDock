# Architecture Clarification: Schema vs SDK Responsibilities

**Issue:** Original SCHEMA_PACKAGE_SPEC.md incorrectly placed file I/O in schema package  
**Resolution:** Schema does validation only, SDK handles file I/O  
**Date:** November 11, 2024

---

## The Correct Pattern

### ❌ Wrong (Original SCHEMA_PACKAGE_SPEC.md)

```python
# Schema package (WRONG - has file I/O)
def load_dockfile(path: str) -> DockSpec:
    """Schema shouldn't do file I/O"""
    data = yaml.safe_load(open(path, "r"))  # ❌ File I/O
    return DockSpec.model_validate(data)
```

**Problems:**
- Schema package depends on file system
- Harder to test (need file mocking)
- Less flexible (can't validate data from APIs, databases)
- Violates separation of concerns

---

### ✅ Correct (Current Implementation)

```python
# Schema package (CORRECT - validation only)
class DockSpec(BaseModel):
    """Pure validation, no I/O"""
    version: Literal["1.0"]
    agent: AgentCfg
    # ... validation logic only

# SDK package (CORRECT - handles I/O)
def load_dockspec(path: str) -> DockSpec:
    """SDK does file I/O, schema does validation"""
    data = yaml.safe_load(open(path, "r"))  # ✅ SDK handles I/O
    return DockSpec.model_validate(data)     # ✅ Schema validates
```

**Benefits:**
- ✅ Schema is pure validation (no side effects)
- ✅ Easy to test (just pass dicts)
- ✅ Flexible (works with files, APIs, databases, memory)
- ✅ Clear separation of concerns

---

## Responsibility Matrix

| Operation | Package | Reasoning |
|-----------|---------|-----------|
| **Read file from disk** | SDK/CLI | File I/O is SDK responsibility |
| **Parse YAML string to dict** | SDK/CLI | Uses PyYAML library |
| **Validate dict structure** | Schema | Pydantic model validation |
| **Expand environment variables** | SDK | Reads from `os.environ` (I/O) |
| **Format error messages** | Schema | Part of validation |
| **Serialize model to YAML** | Schema | Model operation (not file I/O) |
| **Write YAML to file** | SDK/CLI | File I/O |

---

## Code Examples

### Schema Package (`packages/schema/`)

```python
# dockfile_v1.py - Pure validation
from pydantic import BaseModel, field_validator
from typing import Literal

class AgentCfg(BaseModel):
    name: str
    entrypoint: str
    framework: Literal["langgraph", "langchain"]

class DockSpec(BaseModel):
    version: Literal["1.0"]
    agent: AgentCfg
    
    @field_validator("agent")
    @classmethod
    def validate_agent_entrypoint(cls, v):
        if ":" not in v.entrypoint:
            raise ValueError("Entrypoint must be 'module:callable'")
        return v

# serialization.py - Model operations (no file I/O)
def to_yaml_string(spec: DockSpec) -> str:
    """Convert model to YAML string (not file)"""
    import yaml
    return yaml.dump(spec.model_dump())

def from_dict(data: dict) -> DockSpec:
    """Convenience wrapper"""
    return DockSpec.model_validate(data)
```

---

### SDK Package (`packages/sdk-python/`)

```python
# client.py - File I/O and orchestration
import yaml
from dockrion_schema.dockfile_v1 import DockSpec

def load_dockspec(path: str) -> DockSpec:
    """Load and validate Dockfile from disk"""
    # Step 1: Read file (I/O - SDK's job)
    with open(path, "r") as f:
        content = f.read()
    
    # Step 2: Parse YAML (I/O operation - SDK's job)
    data = yaml.safe_load(content)
    
    # Step 3: Expand environment variables (I/O - SDK's job)
    data = expand_env_vars(data)
    
    # Step 4: Validate (calls schema)
    return DockSpec.model_validate(data)

def expand_env_vars(data: dict) -> dict:
    """Replace ${VAR} with environment values"""
    import os
    import re
    
    def replace_env(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    
    # Recursively expand environment variables
    # ... implementation
    return data

def save_dockspec(spec: DockSpec, path: str) -> None:
    """Save validated spec to file"""
    # Use schema's serialization
    from dockrion_schema.serialization import to_yaml_string
    yaml_content = to_yaml_string(spec)
    
    # SDK handles file writing
    with open(path, "w") as f:
        f.write(yaml_content)
```

---

### CLI Package (`packages/cli/`)

```python
# validate_cmd.py - Uses SDK
from dockrion_sdk.client import load_dockspec
from dockrion_common.errors import ValidationError
import typer

@app.command()
def validate(path: str = "Dockfile.yaml"):
    """Validate Dockfile configuration"""
    try:
        # CLI delegates to SDK for file loading
        spec = load_dockspec(path)
        typer.echo(f"✅ Dockfile valid: {spec.agent.name}")
    except ValidationError as e:
        typer.echo(f"❌ Validation failed: {e.message}")
        raise typer.Exit(1)
```

---

## Testing Strategy

### Schema Tests (Pure, No Mocking)

```python
# test_schema.py - Fast, no file I/O
def test_dockspec_validation():
    """Test validation with plain dicts"""
    data = {
        "version": "1.0",
        "agent": {
            "name": "test-agent",
            "entrypoint": "app.main:build_graph",
            "framework": "langgraph"
        }
    }
    
    spec = DockSpec.model_validate(data)
    assert spec.agent.name == "test-agent"

def test_invalid_entrypoint():
    """Test validation catches errors"""
    data = {
        "version": "1.0",
        "agent": {
            "name": "test-agent",
            "entrypoint": "missing_colon",  # Invalid!
            "framework": "langgraph"
        }
    }
    
    with pytest.raises(ValidationError):
        DockSpec.model_validate(data)
```

### SDK Tests (File I/O)

```python
# test_sdk.py - Tests file operations
def test_load_dockspec_from_file(tmp_path):
    """Test loading from actual file"""
    dockfile = tmp_path / "Dockfile.yaml"
    dockfile.write_text("""
version: "1.0"
agent:
  name: test-agent
  entrypoint: app.main:build_graph
  framework: langgraph
    """)
    
    spec = load_dockspec(str(dockfile))
    assert spec.agent.name == "test-agent"
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ USER                                                         │
│   ↓                                                          │
│   Creates Dockfile.yaml (YAML file on disk)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ CLI / SDK (File I/O Layer)                                  │
│                                                               │
│   1. Read file from disk: open("Dockfile.yaml")            │
│   2. Parse YAML to dict: yaml.safe_load()                   │
│   3. Expand env vars: ${VAR} → os.environ["VAR"]           │
│                                                               │
│   Result: Python dict                                        │
└────────────────────────┬────────────────────────────────────┘
                         │ (passes dict)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ SCHEMA (Validation Layer)                                   │
│                                                               │
│   1. Receive dict (no file knowledge)                        │
│   2. Validate structure: DockSpec.model_validate(data)      │
│   3. Check types, required fields, formats                   │
│   4. Run custom validators                                   │
│                                                               │
│   Result: Validated DockSpec object                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ APPLICATION LOGIC                                            │
│                                                               │
│   - Deploy agent (SDK)                                       │
│   - Generate runtime (SDK)                                   │
│   - Store in database (Controller)                           │
│   - Display in UI (Dashboard)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Principles

### 1. Schema is Pure
- **No file system access**: Doesn't read/write files
- **No network access**: Doesn't make HTTP calls
- **No environment access**: Doesn't read `os.environ`
- **Pure validation**: Input dict → Output validated object or error

### 2. SDK is I/O Layer
- **Handles all file operations**: Read/write Dockfiles
- **Handles all parsing**: YAML ↔ dict conversion
- **Handles environment expansion**: `${VAR}` substitution
- **Orchestrates validation**: Calls schema after preparing data

### 3. Clear Boundary
```python
# This is the boundary:
dict → Schema → DockSpec
     ↑
     |
   SDK handles everything before this arrow
```

---

## Migration Notes

If schema package was already implemented with file I/O:

### Step 1: Move Functions
```python
# Move from schema/parser.py to sdk/client.py:
- load_dockfile(path) → load_dockspec(path)
- expand_env_vars(data)
- read_yaml_file(path)
```

### Step 2: Keep in Schema
```python
# Keep in schema/serialization.py:
- to_yaml_string(spec) → YAML string (not file)
- to_dict(spec) → dict
- from_dict(data) → DockSpec
```

### Step 3: Update Imports
```python
# Before (wrong):
from dockrion_schema.parser import load_dockfile

# After (correct):
from dockrion_sdk.client import load_dockspec
```

---

## Why This Matters

### Without Clear Separation:
- ❌ Schema package has unnecessary dependencies
- ❌ Harder to test (need file system mocking)
- ❌ Less reusable (can't validate API responses)
- ❌ More coupling between layers

### With Clear Separation:
- ✅ Schema is pure, testable, reusable
- ✅ SDK provides convenient high-level API
- ✅ Each package has single responsibility
- ✅ Easy to extend (add new sources: API, database, etc.)

---

## Summary

| Aspect | Schema Package | SDK Package |
|--------|----------------|-------------|
| **Purpose** | Validate data structure | Orchestrate operations |
| **Input** | Python dict | File path (string) |
| **Output** | DockSpec or ValidationError | DockSpec (after I/O) |
| **Dependencies** | pydantic only | schema, pyyaml, common |
| **Side Effects** | None (pure) | File I/O, env access |
| **Testing** | Pass dicts directly | Need file system |

**Golden Rule:** If it touches anything outside the Python process (files, network, environment), it belongs in SDK, not schema.

