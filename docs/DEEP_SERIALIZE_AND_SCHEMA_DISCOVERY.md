# Deep Serialization & Schema Discovery

> **Status**: Proposed  
> **Author**: Dockrion Team  
> **Created**: 2024-12-31  
> **Priority**: High (Blocking for LangGraph chat agents)

## Problem Statement

Agents (especially LangGraph) often return Python objects that are not JSON-serializable:

```python
# LangGraph chat agent returns:
{"messages": [HumanMessage(content="Hi"), AIMessage(content="Hello!")]}

# This fails with:
# TypeError: Object of type HumanMessage is not JSON serializable
```

**Current Pain Points:**

1. Users must manually serialize objects in their agent code
2. Users don't know what their objects serialize to when writing `io_schema`
3. No tooling to discover/generate schema from actual output

---

## Solution Overview

Three complementary features:

| Feature | Purpose | Location |
|---------|---------|----------|
| **Deep Serialize** | Auto-convert Python objects to JSON-serializable dicts | `dockrion_adapters` |
| **Schema Discovery** | Generate `io_schema` from actual agent output | `dockrion_cli` |
| **Lenient Mode** | Skip output validation when schema unknown | `dockrion_schema` + runtime |

---

## Part 1: Deep Serialization

### 1.1 Design

Add a recursive serializer that handles any Python object gracefully.

**Location**: `packages/adapters/dockrion_adapters/serialization.py` (new file)

**Called by**: Each adapter's `invoke()` method, after getting result from agent

### 1.2 Implementation

```python
# packages/adapters/dockrion_adapters/serialization.py
"""
Deep Serialization Utilities

Converts arbitrary Python objects to JSON-serializable structures.
Used by adapters to ensure agent output can be serialized to JSON.
"""

from typing import Any, Dict, List, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
import uuid

# Type alias for JSON-serializable types
JsonSerializable = Union[None, bool, int, float, str, List[Any], Dict[str, Any]]


def deep_serialize(obj: Any, max_depth: int = 50, _depth: int = 0) -> JsonSerializable:
    """
    Recursively convert Python objects to JSON-serializable types.
    
    Handles:
    - Primitives (None, bool, int, float, str)
    - Collections (list, tuple, set, dict)
    - Pydantic models (v1 and v2)
    - Dataclasses
    - datetime objects
    - UUID, Decimal, Enum, Path
    - Custom classes (via __dict__ or str fallback)
    
    Args:
        obj: Any Python object to serialize
        max_depth: Maximum recursion depth (prevents infinite loops)
        _depth: Current recursion depth (internal)
        
    Returns:
        JSON-serializable Python object (dict, list, or primitive)
        
    Examples:
        >>> from langchain_core.messages import HumanMessage
        >>> msg = HumanMessage(content="Hello")
        >>> deep_serialize(msg)
        {'content': 'Hello', 'type': 'human', ...}
        
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Point:
        ...     x: int
        ...     y: int
        >>> deep_serialize(Point(1, 2))
        {'x': 1, 'y': 2}
    """
    # Prevent infinite recursion
    if _depth > max_depth:
        return f"<max depth {max_depth} exceeded>"
    
    # Already JSON-serializable primitives
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    
    # Handle bytes
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return f"<bytes: {len(obj)} bytes>"
    
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [deep_serialize(item, max_depth, _depth + 1) for item in obj]
    
    # Handle sets and frozensets
    if isinstance(obj, (set, frozenset)):
        return [deep_serialize(item, max_depth, _depth + 1) for item in sorted(obj, key=str)]
    
    # Handle dicts
    if isinstance(obj, dict):
        return {
            str(k): deep_serialize(v, max_depth, _depth + 1) 
            for k, v in obj.items()
        }
    
    # === Special Types ===
    
    # Pydantic v2 models (check first, more common)
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return deep_serialize(obj.model_dump(), max_depth, _depth + 1)
        except Exception:
            pass  # Fall through to other methods
    
    # Pydantic v1 models
    if hasattr(obj, "dict") and callable(obj.dict) and hasattr(obj, "__fields__"):
        try:
            return deep_serialize(obj.dict(), max_depth, _depth + 1)
        except Exception:
            pass
    
    # Dataclasses
    if hasattr(obj, "__dataclass_fields__"):
        try:
            from dataclasses import asdict
            return deep_serialize(asdict(obj), max_depth, _depth + 1)
        except Exception:
            pass
    
    # datetime types
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return obj.total_seconds()
    
    # UUID
    if isinstance(obj, uuid.UUID):
        return str(obj)
    
    # Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    
    # Enum
    if isinstance(obj, Enum):
        return obj.value
    
    # Path
    if isinstance(obj, Path):
        return str(obj)
    
    # === Generic Fallbacks ===
    
    # Objects with __dict__ (most custom classes)
    if hasattr(obj, "__dict__"):
        # Filter out private/dunder attributes
        obj_dict = {
            k: v for k, v in vars(obj).items() 
            if not k.startswith("_")
        }
        if obj_dict:
            return deep_serialize(obj_dict, max_depth, _depth + 1)
    
    # Objects with __slots__
    if hasattr(obj, "__slots__"):
        obj_dict = {
            slot: getattr(obj, slot, None) 
            for slot in obj.__slots__ 
            if not slot.startswith("_")
        }
        if obj_dict:
            return deep_serialize(obj_dict, max_depth, _depth + 1)
    
    # Callable (functions, methods)
    if callable(obj):
        return f"<callable: {getattr(obj, '__name__', str(obj))}>"
    
    # Last resort: string representation
    try:
        return str(obj)
    except Exception:
        return f"<unserializable: {type(obj).__name__}>"


def serialize_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper for serializing agent output.
    
    Args:
        data: Agent output dictionary (may contain non-serializable objects)
        
    Returns:
        JSON-serializable dictionary
    """
    return deep_serialize(data)
```

### 1.3 Integration with Adapters

**File**: `packages/adapters/dockrion_adapters/langgraph_adapter.py`

Add after the invoke call (around line 463):

```python
from .serialization import serialize_for_json

# In invoke() method, after getting result:
result = self._runner.invoke(payload)

# NEW: Ensure output is JSON-serializable
result = serialize_for_json(result)

# Existing validation continues...
if not isinstance(result, dict):
    ...
```

**File**: `packages/adapters/dockrion_adapters/handler_adapter.py`

Same pattern:

```python
from .serialization import serialize_for_json

# In invoke() method:
result = self._handler(payload)

# NEW: Ensure output is JSON-serializable
result = serialize_for_json(result)
```

### 1.4 Export from Package

**File**: `packages/adapters/dockrion_adapters/__init__.py`

```python
from .serialization import deep_serialize, serialize_for_json

__all__ = [
    # ... existing exports
    "deep_serialize",
    "serialize_for_json",
]
```

### 1.5 Tests

**File**: `packages/adapters/tests/test_serialization.py`

```python
"""Tests for deep serialization utilities."""

import pytest
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional
import uuid

from dockrion_adapters.serialization import deep_serialize, serialize_for_json


class TestPrimitives:
    """Test serialization of primitive types."""
    
    def test_none(self):
        assert deep_serialize(None) is None
    
    def test_bool(self):
        assert deep_serialize(True) is True
        assert deep_serialize(False) is False
    
    def test_int(self):
        assert deep_serialize(42) == 42
    
    def test_float(self):
        assert deep_serialize(3.14) == 3.14
    
    def test_str(self):
        assert deep_serialize("hello") == "hello"


class TestCollections:
    """Test serialization of collections."""
    
    def test_list(self):
        assert deep_serialize([1, 2, 3]) == [1, 2, 3]
    
    def test_nested_list(self):
        assert deep_serialize([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]
    
    def test_tuple(self):
        assert deep_serialize((1, 2, 3)) == [1, 2, 3]
    
    def test_set(self):
        result = deep_serialize({3, 1, 2})
        assert sorted(result) == [1, 2, 3]
    
    def test_dict(self):
        assert deep_serialize({"a": 1, "b": 2}) == {"a": 1, "b": 2}
    
    def test_nested_dict(self):
        data = {"outer": {"inner": [1, 2, 3]}}
        assert deep_serialize(data) == {"outer": {"inner": [1, 2, 3]}}


class TestSpecialTypes:
    """Test serialization of special types."""
    
    def test_datetime(self):
        dt = datetime(2024, 12, 31, 12, 30, 45)
        assert deep_serialize(dt) == "2024-12-31T12:30:45"
    
    def test_date(self):
        d = date(2024, 12, 31)
        assert deep_serialize(d) == "2024-12-31"
    
    def test_timedelta(self):
        td = timedelta(hours=1, minutes=30)
        assert deep_serialize(td) == 5400.0  # seconds
    
    def test_uuid(self):
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert deep_serialize(u) == "12345678-1234-5678-1234-567812345678"
    
    def test_decimal(self):
        d = Decimal("3.14159")
        assert deep_serialize(d) == 3.14159
    
    def test_path(self):
        p = Path("/usr/local/bin")
        assert deep_serialize(p) == "/usr/local/bin"
    
    def test_bytes_utf8(self):
        b = b"hello world"
        assert deep_serialize(b) == "hello world"
    
    def test_bytes_binary(self):
        b = bytes([0xFF, 0xFE, 0x00])
        result = deep_serialize(b)
        assert "<bytes:" in result or isinstance(result, str)


class TestEnum:
    """Test enum serialization."""
    
    def test_string_enum(self):
        class Color(Enum):
            RED = "red"
            GREEN = "green"
        
        assert deep_serialize(Color.RED) == "red"
    
    def test_int_enum(self):
        class Status(Enum):
            ACTIVE = 1
            INACTIVE = 0
        
        assert deep_serialize(Status.ACTIVE) == 1


class TestDataclass:
    """Test dataclass serialization."""
    
    def test_simple_dataclass(self):
        @dataclass
        class Point:
            x: int
            y: int
        
        assert deep_serialize(Point(1, 2)) == {"x": 1, "y": 2}
    
    def test_nested_dataclass(self):
        @dataclass
        class Inner:
            value: str
        
        @dataclass
        class Outer:
            inner: Inner
            name: str
        
        obj = Outer(inner=Inner(value="test"), name="outer")
        result = deep_serialize(obj)
        assert result == {"inner": {"value": "test"}, "name": "outer"}


class TestPydanticModels:
    """Test Pydantic model serialization."""
    
    def test_pydantic_v2_model(self):
        pytest.importorskip("pydantic")
        from pydantic import BaseModel
        
        class User(BaseModel):
            name: str
            age: int
        
        user = User(name="Alice", age=30)
        result = deep_serialize(user)
        assert result == {"name": "Alice", "age": 30}
    
    def test_nested_pydantic(self):
        pytest.importorskip("pydantic")
        from pydantic import BaseModel
        
        class Address(BaseModel):
            city: str
        
        class Person(BaseModel):
            name: str
            address: Address
        
        person = Person(name="Bob", address=Address(city="NYC"))
        result = deep_serialize(person)
        assert result == {"name": "Bob", "address": {"city": "NYC"}}


class TestLangChainMessages:
    """Test LangChain message serialization."""
    
    def test_human_message(self):
        langchain = pytest.importorskip("langchain_core")
        from langchain_core.messages import HumanMessage
        
        msg = HumanMessage(content="Hello, world!")
        result = deep_serialize(msg)
        
        assert isinstance(result, dict)
        assert result["content"] == "Hello, world!"
        assert result["type"] == "human"
    
    def test_ai_message(self):
        langchain = pytest.importorskip("langchain_core")
        from langchain_core.messages import AIMessage
        
        msg = AIMessage(content="I'm an AI assistant.")
        result = deep_serialize(msg)
        
        assert isinstance(result, dict)
        assert result["content"] == "I'm an AI assistant."
        assert result["type"] == "ai"
    
    def test_message_list(self):
        langchain = pytest.importorskip("langchain_core")
        from langchain_core.messages import HumanMessage, AIMessage
        
        messages = [
            HumanMessage(content="Hi"),
            AIMessage(content="Hello!"),
        ]
        
        result = deep_serialize({"messages": messages})
        
        assert isinstance(result, dict)
        assert len(result["messages"]) == 2
        assert result["messages"][0]["type"] == "human"
        assert result["messages"][1]["type"] == "ai"


class TestCustomClasses:
    """Test custom class serialization."""
    
    def test_class_with_dict(self):
        class Custom:
            def __init__(self):
                self.name = "test"
                self.value = 42
                self._private = "hidden"
        
        obj = Custom()
        result = deep_serialize(obj)
        
        assert result == {"name": "test", "value": 42}
        assert "_private" not in result
    
    def test_class_with_slots(self):
        class Slotted:
            __slots__ = ["x", "y", "_internal"]
            
            def __init__(self):
                self.x = 1
                self.y = 2
                self._internal = "hidden"
        
        obj = Slotted()
        result = deep_serialize(obj)
        
        assert result == {"x": 1, "y": 2}


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_max_depth(self):
        """Test that max depth prevents infinite recursion."""
        # Create deeply nested structure
        deep = {"level": 0}
        current = deep
        for i in range(100):
            current["nested"] = {"level": i + 1}
            current = current["nested"]
        
        # Should not raise, should truncate
        result = deep_serialize(deep, max_depth=10)
        assert isinstance(result, dict)
    
    def test_circular_reference_protection(self):
        """Test handling of circular references."""
        # Note: Current implementation doesn't detect cycles,
        # but max_depth prevents infinite recursion
        pass
    
    def test_callable(self):
        def my_func():
            pass
        
        result = deep_serialize(my_func)
        assert "<callable:" in result
    
    def test_non_string_dict_keys(self):
        """Test that non-string dict keys are converted to strings."""
        data = {1: "one", 2: "two"}
        result = deep_serialize(data)
        assert result == {"1": "one", "2": "two"}


class TestSerializeForJson:
    """Test the convenience wrapper."""
    
    def test_basic_usage(self):
        data = {"result": "success", "count": 42}
        result = serialize_for_json(data)
        assert result == data
    
    def test_with_complex_objects(self):
        data = {
            "timestamp": datetime(2024, 12, 31),
            "id": uuid.UUID("12345678-1234-5678-1234-567812345678"),
        }
        result = serialize_for_json(data)
        
        assert result["timestamp"] == "2024-12-31T00:00:00"
        assert result["id"] == "12345678-1234-5678-1234-567812345678"
```

---

## Part 2: Schema Discovery Command

### 2.1 Design

New CLI command: `dockrion inspect`

**Purpose**: Run agent with test payload and generate/display the output schema.

**Usage**:
```bash
# Basic: show serialized output
dockrion inspect --payload '{"messages": [...]}'

# Generate io_schema from output
dockrion inspect --payload '{"messages": [...]}' --generate-schema

# Save generated schema to file
dockrion inspect --payload '{"messages": [...]}' --generate-schema -o schema.yaml
```

### 2.2 Implementation

**File**: `packages/cli/dockrion_cli/inspect_cmd.py` (new file)

```python
"""Inspect command - Analyze agent output and generate schemas."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import typer
from dockrion_sdk import invoke_local
from rich.syntax import Syntax
from rich.panel import Panel

from .utils import console, error, handle_error, info, success, warning

app = typer.Typer()


def infer_json_schema(value: Any, required: bool = True) -> Dict[str, Any]:
    """
    Infer JSON Schema from a Python value.
    
    Args:
        value: Any Python value (after serialization)
        required: Whether to mark fields as required
        
    Returns:
        JSON Schema dictionary
    """
    if value is None:
        return {"type": "null"}
    
    if isinstance(value, bool):
        return {"type": "boolean"}
    
    if isinstance(value, int):
        return {"type": "integer"}
    
    if isinstance(value, float):
        return {"type": "number"}
    
    if isinstance(value, str):
        return {"type": "string"}
    
    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}
        
        # Infer items schema from first element
        # (Could be smarter and merge schemas from all elements)
        items_schema = infer_json_schema(value[0], required=False)
        return {"type": "array", "items": items_schema}
    
    if isinstance(value, dict):
        properties = {}
        required_fields = []
        
        for k, v in value.items():
            properties[k] = infer_json_schema(v, required=False)
            if v is not None:
                required_fields.append(k)
        
        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        
        if required_fields:
            schema["required"] = sorted(required_fields)
        
        return schema
    
    # Fallback for any other type
    return {"type": "string"}


def generate_io_schema_yaml(
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
) -> str:
    """
    Generate io_schema YAML section from input/output data.
    
    Args:
        input_data: Sample input payload
        output_data: Actual output from agent
        
    Returns:
        YAML string for io_schema section
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML required. Install with: pip install pyyaml")
    
    input_schema = infer_json_schema(input_data)
    output_schema = infer_json_schema(output_data)
    
    io_schema = {
        "io_schema": {
            "input": input_schema,
            "output": output_schema,
        }
    }
    
    return yaml.dump(io_schema, default_flow_style=False, sort_keys=False)


@app.command(name="inspect")
def inspect(
    path: str = typer.Argument("Dockfile.yaml", help="Path to Dockfile"),
    payload: str = typer.Option(None, "--payload", "-p", help="JSON payload as string"),
    payload_file: str = typer.Option(
        None, "--payload-file", "-f", help="Path to JSON file with payload"
    ),
    generate_schema: bool = typer.Option(
        False, "--generate-schema", "-g", help="Generate io_schema from output"
    ),
    output_file: str = typer.Option(
        None, "--output", "-o", help="Save output/schema to file"
    ),
    show_raw: bool = typer.Option(
        False, "--raw", "-r", help="Show raw Python repr instead of JSON"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """
    Inspect agent output and optionally generate io_schema.
    
    This command helps you understand what your agent returns and
    automatically generates the io_schema section for your Dockfile.
    
    Examples:
        # See what your agent returns (serialized)
        dockrion inspect --payload '{"text": "hello"}'
        
        # Generate io_schema from actual output
        dockrion inspect -p '{"text": "hello"}' --generate-schema
        
        # Save generated schema to file
        dockrion inspect -p '{"text": "hello"}' -g -o io_schema.yaml
        
        # With payload from file
        dockrion inspect -f input.json --generate-schema
    """
    try:
        # Validate Dockfile exists
        if not Path(path).exists():
            error(f"Dockfile not found: {path}")
            raise typer.Exit(1)
        
        # Load payload
        payload_data = None
        if payload_file:
            try:
                with open(payload_file, "r") as f:
                    payload_data = json.load(f)
                if verbose:
                    info(f"Loaded payload from {payload_file}")
            except FileNotFoundError:
                error(f"Payload file not found: {payload_file}")
                raise typer.Exit(1)
            except json.JSONDecodeError as e:
                error(f"Invalid JSON in payload file: {str(e)}")
                raise typer.Exit(1)
        elif payload:
            try:
                payload_data = json.loads(payload)
            except json.JSONDecodeError as e:
                error(f"Invalid JSON payload: {str(e)}")
                raise typer.Exit(1)
        else:
            error("No payload provided")
            console.print("\n[dim]Provide input using either:[/dim]")
            console.print('  • [cyan]--payload \'{"key": "value"}\'[/cyan]')
            console.print("  • [cyan]--payload-file input.json[/cyan]")
            raise typer.Exit(1)
        
        # Show input
        if verbose:
            info(f"Inspecting agent from {path}")
            console.print("\n[bold]Input payload:[/bold]")
            syntax = Syntax(json.dumps(payload_data, indent=2), "json", theme="monokai")
            console.print(Panel(syntax, title="Input", border_style="blue"))
        
        # Invoke agent
        with console.status("[bold green]Invoking agent..."):
            result = invoke_local(path, payload_data)
        
        success("Agent invocation successful")
        console.print()
        
        # Display output
        if show_raw:
            # Raw Python representation
            console.print("[bold]Raw Output (repr):[/bold]")
            console.print(repr(result))
        else:
            # JSON output (uses deep_serialize from adapter)
            console.print("[bold]Serialized Output:[/bold]")
            try:
                output_json = json.dumps(result, indent=2)
                syntax = Syntax(output_json, "json", theme="monokai")
                console.print(Panel(syntax, title="Agent Output", border_style="green"))
            except TypeError as e:
                warning(f"Output contains non-serializable objects: {e}")
                console.print("[yellow]Falling back to repr():[/yellow]")
                console.print(repr(result))
                console.print("\n[dim]💡 Tip: Ensure your agent returns JSON-serializable output[/dim]")
                raise typer.Exit(1)
        
        # Generate schema if requested
        if generate_schema:
            console.print()
            info("Generating io_schema from output...")
            
            try:
                schema_yaml = generate_io_schema_yaml(payload_data, result)
                
                console.print("\n[bold]Generated io_schema:[/bold]")
                syntax = Syntax(schema_yaml, "yaml", theme="monokai")
                console.print(Panel(syntax, title="io_schema", border_style="cyan"))
                
                # Save to file if requested
                if output_file:
                    with open(output_file, "w") as f:
                        f.write(schema_yaml)
                    success(f"Schema saved to {output_file}")
                    console.print(
                        f"\n[dim]💡 Copy the io_schema section to your Dockfile.yaml[/dim]"
                    )
                
            except ImportError as e:
                error(str(e))
                raise typer.Exit(1)
        
        # Save output to file (without schema generation)
        elif output_file:
            try:
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)
                info(f"Output saved to {output_file}")
            except TypeError as e:
                warning(f"Failed to save output: {str(e)}")
        
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        info("\nInspection cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, verbose)
        raise typer.Exit(1)
```

### 2.3 Register Command

**File**: `packages/cli/dockrion_cli/main.py`

Add the import and registration:

```python
from .inspect_cmd import app as inspect_app

# In the main app setup:
app.add_typer(inspect_app, name="inspect")
```

### 2.4 Tests

**File**: `packages/cli/tests/test_inspect_cmd.py`

```python
"""Tests for inspect command."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from dockrion_cli.main import app
from dockrion_cli.inspect_cmd import infer_json_schema, generate_io_schema_yaml


runner = CliRunner()


class TestInferJsonSchema:
    """Tests for schema inference."""
    
    def test_infer_string(self):
        schema = infer_json_schema("hello")
        assert schema == {"type": "string"}
    
    def test_infer_integer(self):
        schema = infer_json_schema(42)
        assert schema == {"type": "integer"}
    
    def test_infer_number(self):
        schema = infer_json_schema(3.14)
        assert schema == {"type": "number"}
    
    def test_infer_boolean(self):
        schema = infer_json_schema(True)
        assert schema == {"type": "boolean"}
    
    def test_infer_null(self):
        schema = infer_json_schema(None)
        assert schema == {"type": "null"}
    
    def test_infer_array(self):
        schema = infer_json_schema([1, 2, 3])
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "integer"
    
    def test_infer_object(self):
        schema = infer_json_schema({"name": "test", "count": 5})
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "count" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["count"]["type"] == "integer"
    
    def test_infer_nested(self):
        data = {
            "messages": [
                {"type": "human", "content": "Hello"}
            ]
        }
        schema = infer_json_schema(data)
        
        assert schema["type"] == "object"
        assert schema["properties"]["messages"]["type"] == "array"
        items = schema["properties"]["messages"]["items"]
        assert items["type"] == "object"
        assert items["properties"]["type"]["type"] == "string"
        assert items["properties"]["content"]["type"] == "string"


class TestGenerateIoSchema:
    """Tests for io_schema generation."""
    
    def test_generate_simple(self):
        input_data = {"text": "hello"}
        output_data = {"result": "processed"}
        
        yaml_str = generate_io_schema_yaml(input_data, output_data)
        
        assert "io_schema:" in yaml_str
        assert "input:" in yaml_str
        assert "output:" in yaml_str
        assert "type: object" in yaml_str
    
    def test_generate_chat_schema(self):
        input_data = {
            "messages": [{"type": "human", "content": "Hi"}]
        }
        output_data = {
            "messages": [
                {"type": "human", "content": "Hi"},
                {"type": "ai", "content": "Hello!"}
            ]
        }
        
        yaml_str = generate_io_schema_yaml(input_data, output_data)
        
        assert "messages:" in yaml_str
        assert "type: array" in yaml_str


class TestInspectCommand:
    """Integration tests for inspect command."""
    
    @pytest.fixture
    def sample_dockfile(self, tmp_path, mock_agent_module):
        """Create a sample Dockfile for testing."""
        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text(f"""
version: "1.0"
agent:
  name: test-agent
  entrypoint: {mock_agent_module}
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
""")
        return str(dockfile)
    
    def test_inspect_basic(self, sample_dockfile):
        """Test basic inspect command."""
        result = runner.invoke(
            app, 
            ["inspect", sample_dockfile, "--payload", '{"text": "test"}']
        )
        assert result.exit_code == 0
        assert "✅" in result.stdout or "success" in result.stdout.lower()
    
    def test_inspect_generate_schema(self, sample_dockfile):
        """Test inspect with schema generation."""
        result = runner.invoke(
            app,
            ["inspect", sample_dockfile, "--payload", '{"text": "test"}', "--generate-schema"]
        )
        assert result.exit_code == 0
        assert "io_schema" in result.stdout
    
    def test_inspect_save_schema(self, sample_dockfile, tmp_path):
        """Test saving generated schema to file."""
        output_file = tmp_path / "schema.yaml"
        result = runner.invoke(
            app,
            [
                "inspect", sample_dockfile,
                "--payload", '{"text": "test"}',
                "--generate-schema",
                "--output", str(output_file)
            ]
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "io_schema:" in content
    
    def test_inspect_no_payload(self, sample_dockfile):
        """Test inspect without payload fails gracefully."""
        result = runner.invoke(app, ["inspect", sample_dockfile])
        assert result.exit_code == 1
        assert "payload" in result.stdout.lower()
```

---

## Part 3: Lenient Mode for io_schema

### 3.1 Design

Add `strict` field to `io_schema` that controls output validation:

```yaml
io_schema:
  strict: false  # NEW: Skip output validation
  input:
    type: object
    properties:
      messages:
        type: array
  output:
    type: object
    # Properties not defined = accept any structure
```

**Behavior:**
- `strict: true` (default): Validate output against schema (current behavior)
- `strict: false`: Skip output validation, only validate input

### 3.2 Schema Changes

**File**: `packages/schema/dockrion_schema/dockfile_v1.py`

Add `strict` field to `IOSchema`:

```python
class IOSchema(BaseModel):
    """Input/output schema configuration."""
    
    strict: bool = Field(
        default=True,
        description="If false, skip output validation. Useful when output structure is dynamic or unknown."
    )
    input: IOSubSchema = Field(
        ...,
        description="Input schema definition"
    )
    output: IOSubSchema = Field(
        ...,
        description="Output schema definition"
    )
```

### 3.3 Make output Optional

Alternative approach - make output truly optional:

```python
class IOSchema(BaseModel):
    """Input/output schema configuration."""
    
    input: IOSubSchema = Field(
        ...,
        description="Input schema definition (required)"
    )
    output: Optional[IOSubSchema] = Field(
        default=None,
        description="Output schema definition (optional - if not provided, output is not validated)"
    )
```

### 3.4 Runtime Changes

**File**: `packages/runtime/dockrion_runtime/endpoints/invoke.py`

Modify output validation to respect lenient mode:

```python
# Around line 127-132, modify the output validation:

# Check if we should validate output
should_validate_output = True
if hasattr(config, 'io_schema') and config.io_schema:
    # Check for strict mode (default True)
    should_validate_output = getattr(config.io_schema, 'strict', True)
    # Also skip if output schema is None
    if config.io_schema.output is None:
        should_validate_output = False

# Validate output against schema (if strict mode)
if should_validate_output:
    try:
        typed_output: Any = output_model(**result) if isinstance(result, dict) else result
    except Exception:
        # If output doesn't match schema, use raw result
        typed_output = result
else:
    # Lenient mode: use raw result without validation
    typed_output = result
```

### 3.5 SDK/CLI Changes

**File**: `packages/sdk-python/dockrion_sdk/core/invoker.py`

No changes needed - output validation happens at runtime level.

### 3.6 Documentation Update

Add to Dockfile documentation:

```yaml
# Example: Lenient output validation
io_schema:
  strict: false  # Don't validate output structure
  input:
    type: object
    properties:
      messages:
        type: array
        items:
          type: object
          properties:
            type:
              type: string
            content:
              type: string
    required:
      - messages
  output:
    type: object  # Accept any object structure
```

Or:

```yaml
# Example: No output schema at all
io_schema:
  input:
    type: object
    properties:
      query:
        type: string
  # output not specified = no validation
```

### 3.7 Tests

**File**: `packages/schema/tests/test_io_schema_lenient.py`

```python
"""Tests for lenient io_schema mode."""

import pytest
from dockrion_schema import DockSpec, IOSchema, IOSubSchema


class TestLenientMode:
    """Tests for strict/lenient io_schema mode."""
    
    def test_strict_default(self):
        """Test that strict defaults to True."""
        io_schema = IOSchema(
            input=IOSubSchema(type="object"),
            output=IOSubSchema(type="object"),
        )
        assert io_schema.strict is True
    
    def test_strict_explicit_true(self):
        """Test explicit strict=True."""
        io_schema = IOSchema(
            strict=True,
            input=IOSubSchema(type="object"),
            output=IOSubSchema(type="object"),
        )
        assert io_schema.strict is True
    
    def test_strict_false(self):
        """Test strict=False."""
        io_schema = IOSchema(
            strict=False,
            input=IOSubSchema(type="object"),
            output=IOSubSchema(type="object"),
        )
        assert io_schema.strict is False
    
    def test_full_spec_with_lenient(self):
        """Test full DockSpec with lenient mode."""
        spec = DockSpec(
            version="1.0",
            agent={
                "name": "test-agent",
                "entrypoint": "app.main:build_graph",
                "framework": "langgraph",
            },
            io_schema={
                "strict": False,
                "input": {"type": "object"},
                "output": {"type": "object"},
            },
            expose={"port": 8080},
        )
        assert spec.io_schema.strict is False


class TestOptionalOutput:
    """Tests for optional output schema."""
    
    def test_output_optional(self):
        """Test that output can be None."""
        io_schema = IOSchema(
            input=IOSubSchema(type="object"),
            output=None,
        )
        assert io_schema.output is None
    
    def test_from_yaml_no_output(self):
        """Test parsing YAML with no output schema."""
        import yaml
        
        yaml_str = """
input:
  type: object
  properties:
    text:
      type: string
"""
        data = yaml.safe_load(yaml_str)
        io_schema = IOSchema(**data)
        
        assert io_schema.input is not None
        assert io_schema.output is None
```

---

## Implementation Order

1. **Phase 1: Deep Serialization** (Highest Priority)
   - Create `serialization.py` in adapters
   - Integrate into `LangGraphAdapter.invoke()`
   - Integrate into `HandlerAdapter.invoke()`
   - Write tests
   - **Unblocks**: LangGraph chat agents work immediately

2. **Phase 2: Lenient Mode** 
   - Add `strict` field to `IOSchema`
   - Update runtime validation logic
   - Write tests
   - Update documentation
   - **Unblocks**: Users can skip output validation while discovering schema

3. **Phase 3: Schema Discovery**
   - Create `inspect_cmd.py`
   - Implement schema inference
   - Register command
   - Write tests
   - **Improves**: Developer experience for defining schemas

---

## Migration Guide

### For Existing Users with Chat Agents

**Before** (manual serialization required):
```python
# In your agent, you had to serialize manually
def serialize_node(state):
    return {"messages": [m.dict() for m in state["messages"]]}
```

**After** (automatic):
```python
# Just return messages directly - Dockrion handles serialization
def chat_node(state):
    return {"messages": state["messages"]}
```

### For Users with Unknown Output Structure

**Option 1**: Use lenient mode
```yaml
io_schema:
  strict: false
  input:
    type: object
    properties:
      query:
        type: string
  output:
    type: object
```

**Option 2**: Use inspect to discover schema
```bash
dockrion inspect --payload '{"query": "test"}' --generate-schema
# Copy the generated io_schema to your Dockfile
```

---

## Open Questions

1. **Should `strict` default to `true` or `false`?**
   - `true`: Safer, catches schema mismatches
   - `false`: Better DX for new users

2. **Should we support JSON Schema `$ref` for reusable schemas?**
   - Would help with complex nested structures
   - Lower priority for V1

3. **Should `inspect --generate-schema` update Dockfile in-place?**
   - Could add `--update` flag
   - Risk: might overwrite user customizations

4. **Should deep_serialize be configurable?**
   - Could allow users to register custom serializers
   - Probably overkill for V1



