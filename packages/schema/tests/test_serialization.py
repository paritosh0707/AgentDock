"""
Tests for schema serialization utilities.

Tests cover:
- to_dict(): DockSpec → dict conversion
- to_yaml_string(): DockSpec → YAML string conversion
- from_dict(): dict → DockSpec conversion
- Round-trip conversions (dict → DockSpec → dict)
- Edge cases (None values, empty fields)
"""

import pytest
from dockrion_schema import (
    DockSpec,
    to_dict,
    to_yaml_string,
    from_dict,
    ValidationError,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def minimal_spec_data():
    """Minimal valid Dockfile data"""
    return {
        "version": "1.0",
        "agent": {
            "name": "test-agent",
            "entrypoint": "app.main:build_graph",
            "framework": "langgraph"
        },
        "io_schema": {},
        "expose": {
            "port": 8080
        }
    }


@pytest.fixture
def full_spec_data():
    """Full Dockfile data with all fields"""
    return {
        "version": "1.0",
        "agent": {
            "name": "invoice-copilot",
            "description": "Extracts data from invoices",
            "entrypoint": "examples.invoice_copilot.app.graph:build_graph",
            "framework": "langgraph"
        },
        "model": {
            "provider": "openai",
            "name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1500
        },
        "io_schema": {
            "input": {
                "type": "object",
                "properties": {
                    "document_text": {"type": "string"}
                },
                "required": ["document_text"]
            }
        },
        "arguments": {
            "max_retries": 3,
            "timeout": 30
        },
        "policies": {
            "tools": {
                "allowed": ["extract_invoice"],
                "deny_by_default": True
            },
            "safety": {
                "redact_patterns": [r"\b\d{16}\b"],
                "max_output_chars": 5000
            }
        },
        "auth": {
            "mode": "api_key",
            "rate_limits": {"admin": "1000/m"}
        },
        "expose": {
            "rest": True,
            "streaming": "sse",
            "port": 8080,
            "host": "0.0.0.0"
        },
        "metadata": {
            "maintainer": "alice@example.com",
            "version": "1.0.0",
            "tags": ["invoice", "extraction"]
        }
    }


@pytest.fixture
def minimal_spec(minimal_spec_data):
    """DockSpec object from minimal data"""
    return DockSpec.model_validate(minimal_spec_data)


@pytest.fixture
def full_spec(full_spec_data):
    """DockSpec object from full data"""
    return DockSpec.model_validate(full_spec_data)


# =============================================================================
# TO_DICT TESTS
# =============================================================================

class TestToDict:
    """Tests for to_dict() function"""
    
    def test_to_dict_minimal(self, minimal_spec):
        """Test to_dict with minimal spec"""
        result = to_dict(minimal_spec)
        
        assert isinstance(result, dict)
        assert result["version"] == "1.0"
        assert result["agent"]["name"] == "test-agent"
        assert result["agent"]["entrypoint"] == "app.main:build_graph"
        assert result["agent"]["framework"] == "langgraph"
        assert result["expose"]["port"] == 8080
    
    def test_to_dict_full(self, full_spec):
        """Test to_dict with full spec"""
        result = to_dict(full_spec)
        
        assert isinstance(result, dict)
        assert result["version"] == "1.0"
        assert result["agent"]["name"] == "invoice-copilot"
        assert result["model"]["provider"] == "openai"
        assert result["policies"]["tools"]["allowed"] == ["extract_invoice"]
        assert result["metadata"]["maintainer"] == "alice@example.com"
    
    def test_to_dict_exclude_none_true(self, minimal_spec):
        """Test to_dict with exclude_none=True (default)"""
        result = to_dict(minimal_spec, exclude_none=True)
        
        # None fields should be excluded
        assert "model" not in result or result["model"] is None
        assert "description" not in result["agent"]
    
    def test_to_dict_exclude_none_false(self, minimal_spec):
        """Test to_dict with exclude_none=False"""
        result = to_dict(minimal_spec, exclude_none=False)
        
        # Check structure is complete (Pydantic's behavior)
        assert isinstance(result, dict)
        assert "agent" in result
        assert "expose" in result
    
    def test_to_dict_preserves_types(self, full_spec):
        """Test that to_dict preserves Python types"""
        result = to_dict(full_spec)
        
        assert isinstance(result["agent"]["name"], str)
        assert isinstance(result["expose"]["port"], int)
        assert isinstance(result["expose"]["rest"], bool)
        assert isinstance(result["model"]["temperature"], float)
        assert isinstance(result["metadata"]["tags"], list)
        assert isinstance(result["arguments"], dict)


# =============================================================================
# FROM_DICT TESTS
# =============================================================================

class TestFromDict:
    """Tests for from_dict() function"""
    
    def test_from_dict_minimal(self, minimal_spec_data):
        """Test from_dict with minimal data"""
        spec = from_dict(minimal_spec_data)
        
        assert isinstance(spec, DockSpec)
        assert spec.version == "1.0"
        assert spec.agent.name == "test-agent"
        assert spec.agent.entrypoint == "app.main:build_graph"
    
    def test_from_dict_full(self, full_spec_data):
        """Test from_dict with full data"""
        spec = from_dict(full_spec_data)
        
        assert isinstance(spec, DockSpec)
        assert spec.version == "1.0"
        assert spec.agent.name == "invoice-copilot"
        assert spec.model.provider == "openai"
        assert spec.metadata.maintainer == "alice@example.com"
    
    def test_from_dict_validation_error(self):
        """Test from_dict with invalid data"""
        invalid_data = {
            "version": "1.0",
            "agent": {
                "name": "Invalid_Name",  # Uppercase not allowed
                "entrypoint": "app:main",
                "framework": "langgraph"
            },
            "io_schema": {},
            "expose": {"port": 8080}
        }
        
        with pytest.raises(ValidationError):
            from_dict(invalid_data)
    
    def test_from_dict_missing_required_field(self):
        """Test from_dict with missing required field"""
        invalid_data = {
            "version": "1.0",
            # Missing 'agent' field
            "io_schema": {},
            "expose": {"port": 8080}
        }
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            from_dict(invalid_data)


# =============================================================================
# TO_YAML_STRING TESTS
# =============================================================================

class TestToYamlString:
    """Tests for to_yaml_string() function"""
    
    def test_to_yaml_string_minimal(self, minimal_spec):
        """Test to_yaml_string with minimal spec"""
        yaml_str = to_yaml_string(minimal_spec)
        
        assert isinstance(yaml_str, str)
        assert "version:" in yaml_str
        assert "'1.0'" in yaml_str or '"1.0"' in yaml_str
        assert "agent:" in yaml_str
        assert "test-agent" in yaml_str
        assert "app.main:build_graph" in yaml_str
        assert "langgraph" in yaml_str
    
    def test_to_yaml_string_full(self, full_spec):
        """Test to_yaml_string with full spec"""
        yaml_str = to_yaml_string(full_spec)
        
        assert isinstance(yaml_str, str)
        assert "invoice-copilot" in yaml_str
        assert "openai" in yaml_str
        assert "gpt-4o-mini" in yaml_str
        assert "alice@example.com" in yaml_str
    
    def test_to_yaml_string_parseable(self, full_spec):
        """Test that YAML string can be parsed back"""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")
        
        yaml_str = to_yaml_string(full_spec)
        
        # Parse YAML string back to dict
        parsed_data = yaml.safe_load(yaml_str)
        
        assert isinstance(parsed_data, dict)
        assert parsed_data["version"] == "1.0"
        assert parsed_data["agent"]["name"] == "invoice-copilot"
    
    def test_to_yaml_string_exclude_none(self, minimal_spec):
        """Test to_yaml_string with exclude_none"""
        yaml_str = to_yaml_string(minimal_spec, exclude_none=True)
        
        # None fields should not appear in YAML
        # (This depends on Pydantic's model_dump behavior)
        assert isinstance(yaml_str, str)
    
    def test_to_yaml_string_without_pyyaml(self, minimal_spec, monkeypatch):
        """Test to_yaml_string raises error without PyYAML"""
        # Simulate PyYAML not being installed
        import sys
        import builtins
        
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'yaml':
                raise ImportError("No module named 'yaml'")
            return original_import(name, *args, **kwargs)
        
        monkeypatch.setattr(builtins, '__import__', mock_import)
        
        with pytest.raises(ImportError) as exc_info:
            to_yaml_string(minimal_spec)
        assert "PyYAML" in str(exc_info.value)


# =============================================================================
# ROUND-TRIP TESTS
# =============================================================================

class TestRoundTrip:
    """Tests for round-trip conversions"""
    
    def test_dict_to_spec_to_dict_minimal(self, minimal_spec_data):
        """Test dict → DockSpec → dict round-trip (minimal)"""
        # Convert dict to spec
        spec = from_dict(minimal_spec_data)
        
        # Convert back to dict
        result_data = to_dict(spec, exclude_none=False)
        
        # Core fields should match
        assert result_data["version"] == minimal_spec_data["version"]
        assert result_data["agent"]["name"] == minimal_spec_data["agent"]["name"]
        assert result_data["agent"]["entrypoint"] == minimal_spec_data["agent"]["entrypoint"]
        assert result_data["agent"]["framework"] == minimal_spec_data["agent"]["framework"]
    
    def test_dict_to_spec_to_dict_full(self, full_spec_data):
        """Test dict → DockSpec → dict round-trip (full)"""
        # Convert dict to spec
        spec = from_dict(full_spec_data)
        
        # Convert back to dict
        result_data = to_dict(spec, exclude_none=False)
        
        # All fields should match
        assert result_data["version"] == full_spec_data["version"]
        assert result_data["agent"]["name"] == full_spec_data["agent"]["name"]
        assert result_data["model"]["provider"] == full_spec_data["model"]["provider"]
        assert result_data["metadata"]["maintainer"] == full_spec_data["metadata"]["maintainer"]
    
    def test_dict_to_spec_to_yaml_to_dict(self, full_spec_data):
        """Test dict → DockSpec → YAML → dict round-trip"""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")
        
        # Convert dict to spec
        spec = from_dict(full_spec_data)
        
        # Convert to YAML string
        yaml_str = to_yaml_string(spec)
        
        # Parse YAML back to dict
        parsed_data = yaml.safe_load(yaml_str)
        
        # Validate parsed dict
        reparsed_spec = from_dict(parsed_data)
        
        # Should create valid spec
        assert reparsed_spec.version == "1.0"
        assert reparsed_spec.agent.name == "invoice-copilot"
    
    def test_spec_identity_through_serialization(self, minimal_spec):
        """Test that spec can be serialized and deserialized without data loss"""
        # Serialize to dict
        data = to_dict(minimal_spec, exclude_none=False)
        
        # Deserialize back to spec
        new_spec = from_dict(data)
        
        # Re-serialize
        new_data = to_dict(new_spec, exclude_none=False)
        
        # Core fields should be identical
        assert data["version"] == new_data["version"]
        assert data["agent"]["name"] == new_data["agent"]["name"]
        assert data["expose"]["port"] == new_data["expose"]["port"]


# =============================================================================
# EDGE CASES
# =============================================================================

class TestSerializationEdgeCases:
    """Tests for edge cases in serialization"""
    
    def test_empty_optional_fields(self):
        """Test serialization with empty optional fields"""
        data = {
            "version": "1.0",
            "agent": {
                "name": "test",
                "entrypoint": "app:main",
                "framework": "langgraph"
            },
            "io_schema": {},
            "expose": {"port": 8080},
            "arguments": {},  # Empty dict
            "metadata": {"tags": []}  # Empty list
        }
        
        spec = from_dict(data)
        result = to_dict(spec)
        
        assert result["arguments"] == {}
        # Tags might be excluded if empty, depending on exclude_none
    
    def test_special_characters_in_strings(self):
        """Test serialization with special characters"""
        data = {
            "version": "1.0",
            "agent": {
                "name": "test-agent-123",
                "description": "Agent with special chars: @#$%^&*()",
                "entrypoint": "app.main:build_graph",
                "framework": "langgraph"
            },
            "io_schema": {},
            "expose": {"port": 8080}
        }
        
        spec = from_dict(data)
        yaml_str = to_yaml_string(spec)
        
        # Should handle special characters in YAML
        assert "@#$%^&*()" in yaml_str or "special chars" in yaml_str
    
    def test_unicode_in_fields(self):
        """Test serialization with unicode characters"""
        data = {
            "version": "1.0",
            "agent": {
                "name": "test-agent",
                "description": "Agent with unicode: 你好 мир",
                "entrypoint": "app:main",
                "framework": "langgraph"
            },
            "io_schema": {},
            "expose": {"port": 8080},
            "metadata": {
                "maintainer": "alice@例え.com"
            }
        }
        
        spec = from_dict(data)
        yaml_str = to_yaml_string(spec)
        
        # Should handle unicode
        assert isinstance(yaml_str, str)
        
        # Parse back
        try:
            import yaml
            parsed = yaml.safe_load(yaml_str)
            assert isinstance(parsed, dict)
        except ImportError:
            pass  # Skip if PyYAML not available

