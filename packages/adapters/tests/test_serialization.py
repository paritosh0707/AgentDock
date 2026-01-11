"""Tests for deep serialization utilities."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import pytest

from dockrion_adapters.serialization import deep_serialize, serialize_for_json


class TestPrimitives:
    """Test serialization of primitive types."""

    def test_none(self):
        assert deep_serialize(None) is None

    def test_bool_true(self):
        assert deep_serialize(True) is True

    def test_bool_false(self):
        assert deep_serialize(False) is False

    def test_int(self):
        assert deep_serialize(42) == 42

    def test_int_negative(self):
        assert deep_serialize(-100) == -100

    def test_int_zero(self):
        assert deep_serialize(0) == 0

    def test_float(self):
        assert deep_serialize(3.14) == 3.14

    def test_float_negative(self):
        assert deep_serialize(-2.5) == -2.5

    def test_str(self):
        assert deep_serialize("hello") == "hello"

    def test_str_empty(self):
        assert deep_serialize("") == ""

    def test_str_unicode(self):
        assert deep_serialize("héllo 世界") == "héllo 世界"


class TestCollections:
    """Test serialization of collections."""

    def test_list(self):
        assert deep_serialize([1, 2, 3]) == [1, 2, 3]

    def test_list_empty(self):
        assert deep_serialize([]) == []

    def test_nested_list(self):
        assert deep_serialize([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]

    def test_tuple(self):
        # Tuples are converted to lists
        assert deep_serialize((1, 2, 3)) == [1, 2, 3]

    def test_tuple_nested(self):
        assert deep_serialize(((1, 2), (3, 4))) == [[1, 2], [3, 4]]

    def test_set(self):
        result = deep_serialize({3, 1, 2})
        assert isinstance(result, list)
        assert sorted(result) == [1, 2, 3]

    def test_set_empty(self):
        assert deep_serialize(set()) == []

    def test_frozenset(self):
        result = deep_serialize(frozenset([3, 1, 2]))
        assert isinstance(result, list)
        assert sorted(result) == [1, 2, 3]

    def test_dict(self):
        assert deep_serialize({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    def test_dict_empty(self):
        assert deep_serialize({}) == {}

    def test_nested_dict(self):
        data = {"outer": {"inner": [1, 2, 3]}}
        assert deep_serialize(data) == {"outer": {"inner": [1, 2, 3]}}

    def test_mixed_collections(self):
        data = {"list": [1, 2], "nested": {"tuple": (3, 4)}}
        result = deep_serialize(data)
        assert result == {"list": [1, 2], "nested": {"tuple": [3, 4]}}


class TestSpecialTypes:
    """Test serialization of special types."""

    def test_datetime(self):
        dt = datetime(2024, 12, 31, 12, 30, 45)
        assert deep_serialize(dt) == "2024-12-31T12:30:45"

    def test_datetime_with_microseconds(self):
        dt = datetime(2024, 12, 31, 12, 30, 45, 123456)
        assert deep_serialize(dt) == "2024-12-31T12:30:45.123456"

    def test_date(self):
        d = date(2024, 12, 31)
        assert deep_serialize(d) == "2024-12-31"

    def test_time(self):
        t = time(12, 30, 45)
        assert deep_serialize(t) == "12:30:45"

    def test_timedelta(self):
        td = timedelta(hours=1, minutes=30)
        assert deep_serialize(td) == 5400.0  # seconds

    def test_timedelta_days(self):
        td = timedelta(days=2, hours=3)
        assert deep_serialize(td) == 2 * 86400 + 3 * 3600  # seconds

    def test_uuid(self):
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert deep_serialize(u) == "12345678-1234-5678-1234-567812345678"

    def test_decimal(self):
        d = Decimal("3.14159")
        assert deep_serialize(d) == 3.14159

    def test_decimal_integer(self):
        d = Decimal("42")
        assert deep_serialize(d) == 42.0

    def test_path_posix(self):
        p = Path("/usr/local/bin")
        assert deep_serialize(p) == "/usr/local/bin" or deep_serialize(p) == "\\usr\\local\\bin"

    def test_path_relative(self):
        p = Path("src/main.py")
        result = deep_serialize(p)
        assert isinstance(result, str)
        assert "src" in result and "main.py" in result

    def test_bytes_utf8(self):
        b = b"hello world"
        assert deep_serialize(b) == "hello world"

    def test_bytes_binary(self):
        b = bytes([0xFF, 0xFE, 0x00])
        result = deep_serialize(b)
        assert isinstance(result, str)
        assert "<bytes:" in result


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

    def test_enum_in_dict(self):
        class Priority(Enum):
            HIGH = "high"
            LOW = "low"

        data = {"priority": Priority.HIGH, "count": 5}
        result = deep_serialize(data)
        assert result == {"priority": "high", "count": 5}


class TestDataclass:
    """Test dataclass serialization."""

    def test_simple_dataclass(self):
        @dataclass
        class Point:
            x: int
            y: int

        assert deep_serialize(Point(1, 2)) == {"x": 1, "y": 2}

    def test_dataclass_with_optional(self):
        @dataclass
        class Config:
            name: str
            value: Optional[int] = None

        assert deep_serialize(Config("test")) == {"name": "test", "value": None}
        assert deep_serialize(Config("test", 42)) == {"name": "test", "value": 42}

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

    def test_dataclass_with_list(self):
        @dataclass
        class Container:
            items: list

        obj = Container(items=[1, 2, 3])
        assert deep_serialize(obj) == {"items": [1, 2, 3]}


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

    def test_pydantic_with_optional(self):
        pytest.importorskip("pydantic")
        from pydantic import BaseModel

        class Config(BaseModel):
            name: str
            debug: Optional[bool] = None

        config = Config(name="test")
        result = deep_serialize(config)
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result.get("debug") is None


class TestLangChainMessages:
    """Test LangChain message serialization."""

    def test_human_message(self):
        pytest.importorskip("langchain_core")
        from langchain_core.messages import HumanMessage  # type: ignore[import-untyped]

        msg = HumanMessage(content="Hello, world!")
        result = deep_serialize(msg)

        assert isinstance(result, dict)
        assert result["content"] == "Hello, world!"
        assert result["type"] == "human"

    def test_ai_message(self):
        pytest.importorskip("langchain_core")
        from langchain_core.messages import AIMessage  # type: ignore[import-untyped]

        msg = AIMessage(content="I'm an AI assistant.")
        result = deep_serialize(msg)

        assert isinstance(result, dict)
        assert result["content"] == "I'm an AI assistant."
        assert result["type"] == "ai"

    def test_message_list(self):
        pytest.importorskip("langchain_core")
        from langchain_core.messages import AIMessage, HumanMessage  # type: ignore[import-untyped]

        messages = [
            HumanMessage(content="Hi"),
            AIMessage(content="Hello!"),
        ]

        result = deep_serialize({"messages": messages})

        assert isinstance(result, dict)
        assert len(result["messages"]) == 2
        assert result["messages"][0]["type"] == "human"
        assert result["messages"][1]["type"] == "ai"

    def test_system_message(self):
        pytest.importorskip("langchain_core")
        from langchain_core.messages import SystemMessage  # type: ignore[import-untyped]

        msg = SystemMessage(content="You are a helpful assistant.")
        result = deep_serialize(msg)

        assert isinstance(result, dict)
        assert result["content"] == "You are a helpful assistant."
        assert result["type"] == "system"


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

        assert isinstance(result, dict)
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

    def test_class_with_nested_objects(self):
        class Inner:
            def __init__(self, value):
                self.value = value

        class Outer:
            def __init__(self):
                self.inner = Inner("test")
                self.count = 5

        obj = Outer()
        result = deep_serialize(obj)
        assert result == {"inner": {"value": "test"}, "count": 5}


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_max_depth(self):
        """Test that max depth prevents infinite recursion."""
        # Create deeply nested structure
        deep: dict[str, Any] = {"level": 0}
        current: dict[str, Any] = deep
        for i in range(100):
            current["nested"] = {"level": i + 1}
            current = current["nested"]  # type: ignore[assignment]

        # Should not raise, should truncate
        result = deep_serialize(deep, max_depth=10)
        assert isinstance(result, dict)

    def test_max_depth_message(self):
        """Test that max depth returns appropriate message."""
        # Create structure that exceeds depth
        deep = {"a": {"b": {"c": {"d": {"e": "value"}}}}}
        result = deep_serialize(deep, max_depth=3)
        # Should have truncated somewhere
        assert isinstance(result, dict)

    def test_callable(self):
        def my_func():
            pass

        result = deep_serialize(my_func)
        assert isinstance(result, str)
        assert "<callable:" in result
        assert "my_func" in result

    def test_lambda(self):
        def my_lambda(x):
            return x + 1

        result = deep_serialize(my_lambda)
        assert isinstance(result, str)
        assert "<callable:" in result

    def test_non_string_dict_keys(self):
        """Test that non-string dict keys are converted to strings."""
        data = {1: "one", 2: "two"}
        result = deep_serialize(data)
        assert result == {"1": "one", "2": "two"}

    def test_mixed_dict_keys(self):
        data = {1: "one", "two": 2, (3, 4): "tuple"}
        result = deep_serialize(data)
        assert isinstance(result, dict)
        assert "1" in result
        assert "two" in result
        assert "(3, 4)" in result

    def test_empty_custom_object(self):
        """Test custom object with no public attributes."""

        class Empty:
            def __init__(self):
                self._private = "hidden"

        obj = Empty()
        result = deep_serialize(obj)
        # Should fall back to string representation
        assert isinstance(result, str)


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

    def test_with_nested_pydantic(self):
        pytest.importorskip("pydantic")
        from pydantic import BaseModel

        class Item(BaseModel):
            name: str
            price: float

        data = {"items": [Item(name="Widget", price=9.99)]}
        result = serialize_for_json(data)

        assert result["items"][0]["name"] == "Widget"
        assert result["items"][0]["price"] == 9.99

    def test_with_langchain_messages(self):
        pytest.importorskip("langchain_core")
        from langchain_core.messages import AIMessage, HumanMessage  # type: ignore[import-untyped]

        data = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
            ]
        }
        result = serialize_for_json(data)

        assert len(result["messages"]) == 2
        assert result["messages"][0]["content"] == "Hello"
        assert result["messages"][1]["content"] == "Hi there!"


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def test_langgraph_chat_output(self):
        """Test typical LangGraph chat agent output."""
        pytest.importorskip("langchain_core")
        from langchain_core.messages import AIMessage, HumanMessage  # type: ignore[import-untyped]

        # Simulate LangGraph chat output
        output = {
            "messages": [
                HumanMessage(content="What is the capital of France?"),
                AIMessage(content="The capital of France is Paris."),
            ]
        }

        result = serialize_for_json(output)

        assert isinstance(result, dict)
        assert "messages" in result
        assert len(result["messages"]) == 2
        assert result["messages"][0]["type"] == "human"
        assert result["messages"][1]["type"] == "ai"
        assert result["messages"][1]["content"] == "The capital of France is Paris."

    def test_mixed_types_output(self):
        """Test output with mixed types."""

        @dataclass
        class Metadata:
            created_at: datetime
            version: str

        output = {
            "status": "success",
            "data": [1, 2, 3],
            "metadata": Metadata(created_at=datetime(2024, 12, 31, 12, 0, 0), version="1.0.0"),
            "id": uuid.UUID("12345678-1234-5678-1234-567812345678"),
        }

        result = serialize_for_json(output)

        assert result["status"] == "success"
        assert result["data"] == [1, 2, 3]
        assert result["metadata"]["created_at"] == "2024-12-31T12:00:00"
        assert result["metadata"]["version"] == "1.0.0"
        assert result["id"] == "12345678-1234-5678-1234-567812345678"
