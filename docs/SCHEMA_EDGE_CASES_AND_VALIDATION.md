# Schema Package - Edge Cases and Validation Coverage

Comprehensive documentation of validation edge cases handled by the `dockrion-schema` package.

---

## Overview

The schema package implements extensive validation to catch configuration errors early and prevent runtime issues. This document catalogs all edge cases we handle.

---

## 1. I/O Schema Validation

### Handled Edge Cases

#### 1.1 JSON Schema Type Validation

**Supported Types**: `object`, `string`, `number`, `integer`, `boolean`, `array`, `null`

```python
# ✅ Valid
{"input": {"type": "string"}}

# ❌ Invalid - unsupported type
{"input": {"type": "custom_type"}}
# Error: "Unsupported JSON Schema type: 'custom_type'"
```

#### 1.2 Array Type Requirements

**Rule**: Arrays must define their `items` schema

```python
# ✅ Valid
{
    "input": {
        "type": "array",
        "items": {"type": "string"}
    }
}

# ❌ Invalid - missing items
{
    "input": {
        "type": "array"
    }
}
# Error: "JSON Schema type 'array' requires 'items' field"
```

#### 1.3 Nested Object Validation

**Rule**: Properties must be valid JSON Schema objects (dicts)

```python
# ✅ Valid - nested objects
{
    "input": {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                }
            }
        }
    }
}

# ❌ Invalid - property not a dict
{
    "input": {
        "type": "object",
        "properties": {
            "field": "string"  # Should be {"type": "string"}
        }
    }
}
# Error: "Property 'field' must be a JSON Schema object (dict)"
```

#### 1.4 Property Name Validation

**Rule**: Property names cannot be empty or whitespace-only

```python
# ❌ Invalid - empty name
{
    "input": {
        "type": "object",
        "properties": {
            "": {"type": "string"}
        }
    }
}
# Error: "Property names cannot be empty or whitespace"

# ❌ Invalid - whitespace only
{
    "input": {
        "type": "object",
        "properties": {
            "   ": {"type": "string"}
        }
    }
}
# Error: "Property names cannot be empty or whitespace"
```

#### 1.5 Required Fields Validation

**Rule**: Required fields must exist in properties

```python
# ✅ Valid
{
    "input": {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        },
        "required": ["name"]
    }
}

# ❌ Invalid - required field not in properties
{
    "input": {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        },
        "required": ["email"]  # email not defined
    }
}
# Error: "Required field 'email' is not defined in properties"
```

#### 1.6 Duplicate Required Fields

**Rule**: Required array cannot have duplicates

```python
# ❌ Invalid - duplicates
{
    "input": {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        },
        "required": ["name", "name"]  # Duplicate
    }
}
# Error: "Duplicate fields in required list: ['name']"
```

#### 1.7 Complex Nested Structures

**Supported**: Arrays of objects, nested arrays, deeply nested objects

```python
# ✅ Valid - complex nesting
{
    "input": {
        "type": "object",
        "properties": {
            "users": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "emails": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
}
```

---

## 2. Agent Configuration Validation

### Handled Edge Cases

#### 2.1 Agent Name Format

**Rule**: Lowercase, alphanumeric, hyphens only

```python
# ✅ Valid
"invoice-copilot"
"my-agent-123"

# ❌ Invalid
"Invoice-Copilot"  # Uppercase
"my_agent"         # Underscore
"my agent"         # Space
```

#### 2.2 Entrypoint Format and Injection Prevention

**Rule**: Must be `module:callable` format, prevents path traversal

```python
# ✅ Valid
"app.main:build_graph"
"module.submodule:function"

# ❌ Invalid - missing colon
"app.main.build_graph"
# Error: "Entrypoint must be in format 'module:callable'"

# ❌ Invalid - path traversal attempt
"../../../etc/passwd:read"
# Error: "Invalid entrypoint format"
```

#### 2.3 Framework Validation

**Rule**: Must be in `SUPPORTED_FRAMEWORKS` from common

```python
# ✅ Valid (from common constants)
"langgraph"
"langchain"

# ❌ Invalid
"custom_framework"
# Error: "Unsupported framework: 'custom_framework'"
```

---

## 3. Model Configuration Validation

### Handled Edge Cases

#### 3.1 Provider Validation

**Rule**: Must be in `SUPPORTED_PROVIDERS` from common

```python
# ✅ Valid
"openai", "azure", "anthropic", "google", "ollama", "custom"

# ❌ Invalid
"unknown_provider"
# Error: "Unsupported provider: 'unknown_provider'"
```

#### 3.2 Temperature Range

**Rule**: Must be between 0 and 2

```python
# ✅ Valid
0.0, 0.7, 1.5, 2.0

# ❌ Invalid
-0.5  # Too low
3.0   # Too high
# Error: "Temperature must be between 0 and 2"
```

#### 3.3 Max Tokens

**Rule**: Must be positive integer

```python
# ✅ Valid
1000, 4096

# ❌ Invalid
0, -100
# Error: "max_tokens must be positive"
```

---

## 4. Expose Configuration Validation

### Handled Edge Cases

#### 4.1 Port Range

**Rule**: Must be 1-65535

```python
# ✅ Valid
8080, 3000, 443

# ❌ Invalid
0      # Too low
70000  # Too high
# Error: "Port must be between 1 and 65535"
```

#### 4.2 Streaming Mode

**Rule**: Must be in `SUPPORTED_STREAMING` from common

```python
# ✅ Valid
"sse", "websocket", "none"

# ❌ Invalid
"grpc"
# Error: "Unsupported streaming mode: 'grpc'"
```

#### 4.3 At Least One Exposure Method

**Rule**: REST or streaming must be enabled

```python
# ✅ Valid
{"rest": True, "streaming": "sse"}
{"rest": True, "streaming": "none"}
{"rest": False, "streaming": "websocket"}

# ❌ Invalid
{"rest": False, "streaming": "none"}
# Error: "At least one exposure method must be enabled"
```

---

## 5. Authentication Configuration Validation

### Handled Edge Cases

#### 5.1 Auth Mode

**Rule**: Must be in `SUPPORTED_AUTH_MODES` from common

```python
# ✅ Valid
"jwt", "api_key", "oauth2"

# ❌ Invalid
"basic"
# Error: "Unsupported auth mode: 'basic'"
```

#### 5.2 Permissions

**Rule**: Must be in `PERMISSIONS` from common

```python
# ✅ Valid permissions
["deploy", "invoke", "view_metrics"]

# ❌ Invalid
["super_admin"]
# Error: "Unknown permission: 'super_admin'"
```

#### 5.3 Rate Limit Format

**Rule**: Must match pattern `\d+/(s|m|h|d)`

```python
# ✅ Valid
"100/m", "1000/h", "50/s"

# ❌ Invalid
"100"        # Missing unit
"100/min"    # Wrong unit format
"abc/m"      # Not a number
# Error: "Invalid rate limit format"
```

#### 5.4 API Key Rotation Days

**Rule**: Must be positive integer

```python
# ✅ Valid
30, 90

# ❌ Invalid
0, -7
# Error: "rotation_days must be positive"
```

---

## 6. Policies Validation

### Handled Edge Cases

#### 6.1 Max Output Characters

**Rule**: Must be positive integer

```python
# ✅ Valid
10000, 50000

# ❌ Invalid
0, -1000
# Error: "max_output_chars must be positive"
```

---

## 7. Observability Configuration Validation

### Handled Edge Cases

#### 7.1 Log Level

**Rule**: Must be in `LOG_LEVELS` from common

```python
# ✅ Valid
"debug", "info", "warn", "error"

# ❌ Invalid
"trace", "verbose"
# Error: "Invalid log level: 'trace'"
```

---

## 8. DockSpec Version Validation

### Handled Edge Cases

#### 8.1 Version Support

**Rule**: Must be in `SUPPORTED_DOCKFILE_VERSIONS` from common

```python
# ✅ Valid
"1.0"

# ❌ Invalid
"2.0", "0.9"
# Error: "Unsupported Dockfile version: '2.0'"
```

---

## 9. General Validation Patterns

### 9.1 Extra Fields Handling

**Rule**: All models use `ConfigDict(extra="allow")` for extensibility

```python
# ✅ Accepted - unknown fields allowed
{
    "version": "1.0",
    "agent": {...},
    "io_schema": {...},
    "expose": {...},
    "future_field": {...}  # Accepted but not validated
}
```

### 9.2 Optional Fields

**Rule**: Optional fields can be `None` or omitted

```python
# ✅ Valid - minimal config
{
    "version": "1.0",
    "agent": {...},
    "io_schema": {...},
    "expose": {...}
    # policies, auth, observability, model all optional
}
```

### 9.3 Empty Collections

**Rule**: Empty lists and dicts are valid

```python
# ✅ Valid
"io_schema": {}
"arguments": {}
"tags": []
"roles": []
```

---

## 10. Security Considerations

### 10.1 Code Injection Prevention

- **Entrypoint validation**: Prevents path traversal (`../../../`)
- **Port validation**: Prevents reserved/invalid ports
- **Whitelisting**: All supported values come from `common` constants

### 10.2 Input Sanitization

- **Property names**: Cannot be empty or whitespace
- **Required fields**: Must exist in properties
- **Type checking**: Strict type validation for all fields

---

## Test Coverage Summary

| Category | Tests | Coverage |
|----------|-------|----------|
| I/O Schema | 16 tests | All edge cases |
| Agent Config | 7 tests | Name, entrypoint, framework |
| Model Config | 5 tests | Provider, temperature, tokens |
| Expose Config | 7 tests | Port, streaming, exposure |
| Auth Config | 4 tests | Mode, permissions, rate limits |
| Policies | 2 tests | Tool policies, safety policies |
| Observability | 2 tests | Log level, metrics |
| Edge Cases | 4 tests | Empty fields, special chars |
| Serialization | 22 tests | Dict/YAML round-trips |

**Total**: 76 tests, **95% code coverage**

---

## Adding New Edge Case Handling

When adding new validation:

1. **Identify the edge case** - What can go wrong?
2. **Add validator** - Use `@field_validator` or `@model_validator`
3. **Write tests** - At least 2 tests (valid case + invalid case)
4. **Use common constants** - Don't hardcode supported values
5. **Clear error messages** - Help users fix the issue
6. **Document it** - Add to this file

### Example Template

```python
@field_validator("new_field")
@classmethod
def validate_new_field(cls, v: str) -> str:
    """Validate new_field meets requirements"""
    if not meets_requirements(v):
        raise ValidationError(
            f"Invalid new_field: '{v}'. "
            f"Reason and expected format"
        )
    return v
```

---

## Known Limitations

### What We Don't Validate

1. **Deep JSON Schema Validation**: We validate structure but not all JSON Schema keywords (e.g., `pattern`, `minimum`, `maximum`)
2. **Entrypoint Existence**: We validate format but don't check if the module/function exists
3. **Semantic Validation**: We don't validate business logic (e.g., if a specific auth mode makes sense for a specific use case)
4. **Environment Variables**: File I/O and env var expansion are SDK/CLI responsibilities

### Why These Are Limitations

- **Separation of Concerns**: Schema validates structure, not runtime availability
- **Performance**: Deep validation would be slow
- **Flexibility**: Users may have valid use cases we haven't considered

---

## Future Enhancements

Potential edge cases to add:

1. **Stricter JSON Schema**: Full JSON Schema Draft 7 validation
2. **Cross-field Validation**: E.g., if `auth.mode="oauth2"`, require oauth2 config
3. **Resource Limits**: Max properties, max nesting depth
4. **Custom Validators**: Allow users to extend validation
5. **Warning System**: Non-fatal warnings for suboptimal configs

---

## References

- JSON Schema Specification: https://json-schema.org/
- Pydantic Validators: https://docs.pydantic.dev/latest/concepts/validators/
- **Dockrion Constants**: [`constants.py`](../packages/common-py/dockrion_common/constants.py)
- **Test Suites**:
  - [`test_models.py`](../../packages/schema/tests/test_models.py)
  - [`test_edge_cases.py`](../../packages/schema/tests/test_edge_cases.py)

---

**Last Updated**: November 12, 2024  
**Coverage**: 95% (265 statements, 13 missing)  
**Tests**: 76 passing

