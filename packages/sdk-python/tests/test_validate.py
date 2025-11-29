"""Tests for validate.py module."""
import pytest
from dockrion_sdk.validate import validate_dockspec, validate
from dockrion_common.errors import ValidationError


class TestValidateDockspec:
    """Tests for validate_dockspec function."""
    
    def test_validate_valid_dockfile(self, sample_dockfile):
        """Test validating a valid Dockfile."""
        result = validate_dockspec(sample_dockfile)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["spec"] is not None
        assert "test-agent" in result["message"]
    
    def test_validate_file_not_found(self):
        """Test validating a non-existent file."""
        result = validate_dockspec("nonexistent.yaml")
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0].lower()
    
    def test_validate_invalid_yaml(self, invalid_yaml_dockfile):
        """Test validating invalid YAML."""
        result = validate_dockspec(invalid_yaml_dockfile)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_validate_with_warnings(self, tmp_path):
        """Test validation with warnings for high temperature."""
        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: hot-agent
  entrypoint: tests.fixtures.mock_agent:build_agent
  framework: langgraph
model:
  provider: openai
  name: gpt-4
  temperature: 1.5
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
""")
        result = validate_dockspec(str(dockfile))
        # Should be valid but with warnings
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("temperature" in w.lower() for w in result["warnings"])
    
    def test_validate_timeout_warning_high(self, tmp_path):
        """Test validation warning for very high timeout."""
        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: slow-agent
  entrypoint: tests.fixtures.mock_agent:build_agent
  framework: langgraph
model:
  provider: openai
  name: gpt-4
io_schema:
  input:
    type: object
  output:
    type: object
arguments:
  timeout_sec: 500
expose:
  port: 8080
""")
        result = validate_dockspec(str(dockfile))
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("timeout" in w.lower() for w in result["warnings"])
    
    def test_validate_timeout_warning_low(self, tmp_path):
        """Test validation warning for very low timeout."""
        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: fast-agent
  entrypoint: tests.fixtures.mock_agent:build_agent
  framework: langgraph
model:
  provider: openai
  name: gpt-4
io_schema:
  input:
    type: object
  output:
    type: object
arguments:
  timeout_sec: 2
expose:
  port: 8080
""")
        result = validate_dockspec(str(dockfile))
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("timeout" in w.lower() for w in result["warnings"])


class TestValidateLegacy:
    """Tests for legacy validate function."""
    
    def test_validate_legacy_success(self, sample_dockfile):
        """Test legacy validate function with valid Dockfile."""
        result = validate(sample_dockfile)
        assert result["valid"] is True
    
    def test_validate_legacy_failure(self):
        """Test legacy validate function with invalid Dockfile."""
        with pytest.raises(ValidationError):
            validate("nonexistent.yaml")

