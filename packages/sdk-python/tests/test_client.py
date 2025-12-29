"""Tests for client.py module."""

import os
import sys
from pathlib import Path

import pytest

# Ensure tests directory is in path for fixture imports
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

from dockrion_common.errors import DockrionError, ValidationError

from dockrion_sdk.client import ControllerClient, expand_env_vars, invoke_local, load_dockspec


class TestLoadDockspec:
    """Tests for load_dockspec function."""

    def test_load_valid_dockspec(self, sample_dockfile):
        """Test loading a valid Dockfile."""
        spec = load_dockspec(sample_dockfile)
        assert spec.agent.name == "test-agent"
        assert spec.agent.framework == "langgraph"
        assert spec.expose.port == 8080

    def test_load_file_not_found(self):
        """Test loading a non-existent Dockfile."""
        with pytest.raises(ValidationError) as exc_info:
            load_dockspec("nonexistent.yaml")
        assert "not found" in str(exc_info.value).lower()

    def test_load_invalid_yaml(self, invalid_yaml_dockfile):
        """Test loading a Dockfile with invalid YAML."""
        with pytest.raises(ValidationError) as exc_info:
            load_dockspec(invalid_yaml_dockfile)
        assert (
            "invalid yaml" in str(exc_info.value).lower() or "yaml" in str(exc_info.value).lower()
        )

    def test_load_empty_file(self, tmp_path):
        """Test loading an empty Dockfile."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        with pytest.raises(ValidationError) as exc_info:
            load_dockspec(str(empty_file))
        assert "empty" in str(exc_info.value).lower()

    def test_load_with_env_vars(self, dockfile_with_env_vars, set_env_vars):
        """Test loading a Dockfile with environment variable expansion."""
        spec = load_dockspec(dockfile_with_env_vars)
        assert spec.agent.name == "test-agent"
        assert spec.expose.port == 8080


class TestExpandEnvVars:
    """Tests for expand_env_vars function."""

    def test_expand_simple_var(self):
        """Test expanding a simple environment variable."""
        os.environ["TEST_VAR"] = "test_value"
        data = {"key": "${TEST_VAR}"}
        result = expand_env_vars(data)
        assert result["key"] == "test_value"

    def test_expand_with_default(self):
        """Test expanding with default value."""
        data = {"key": "${MISSING_VAR:-default_value}"}
        result = expand_env_vars(data)
        assert result["key"] == "default_value"

    def test_expand_missing_var_no_default(self):
        """Test expanding missing variable without default."""
        # Make sure the var doesn't exist
        if "DEFINITELY_MISSING_VAR" in os.environ:
            del os.environ["DEFINITELY_MISSING_VAR"]

        data = {"key": "${DEFINITELY_MISSING_VAR}"}
        with pytest.raises(ValidationError) as exc_info:
            expand_env_vars(data)
        assert "DEFINITELY_MISSING_VAR" in str(exc_info.value)

    def test_expand_nested_dict(self):
        """Test expanding environment variables in nested dict."""
        os.environ["NESTED_VAR"] = "nested_value"
        data = {"outer": {"inner": "${NESTED_VAR}"}}
        result = expand_env_vars(data)
        assert result["outer"]["inner"] == "nested_value"

    def test_expand_in_list(self):
        """Test expanding environment variables in lists."""
        os.environ["LIST_VAR"] = "list_value"
        data = {"items": ["${LIST_VAR}", "static"]}
        result = expand_env_vars(data)
        assert result["items"][0] == "list_value"
        assert result["items"][1] == "static"

    def test_no_expansion_needed(self):
        """Test data without environment variables."""
        data = {"key": "value", "number": 123}
        result = expand_env_vars(data)
        assert result == data


class TestInvokeLocal:
    """Tests for invoke_local function."""

    def test_invoke_local_success(self, sample_dockfile):
        """Test successfully invoking a local agent."""
        # This requires the mock agent to be importable
        result = invoke_local(sample_dockfile, {"text": "test input"})
        assert "result" in result
        assert "test input" in result["result"]

    def test_invoke_local_invalid_dockfile(self, tmp_path):
        """Test invoke_local with invalid Dockfile."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("invalid: yaml: content:")
        with pytest.raises(ValidationError):
            invoke_local(str(bad_file), {"text": "test"})

    def test_invoke_local_invalid_entrypoint(self, tmp_path):
        """Test invoke_local with invalid agent entrypoint."""
        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: bad-agent
  entrypoint: nonexistent.module:function
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
""")
        with pytest.raises(DockrionError):
            invoke_local(str(dockfile), {"text": "test"})


class TestControllerClient:
    """Tests for ControllerClient class."""

    def test_client_initialization(self):
        """Test ControllerClient initialization."""
        client = ControllerClient()
        assert client.base_url == "http://localhost:8000"

    def test_client_custom_url(self):
        """Test ControllerClient with custom URL."""
        client = ControllerClient("http://custom:9000")
        assert client.base_url == "http://custom:9000"

    def test_status_endpoint(self):
        """Test controller status method."""
        client = ControllerClient()
        status = client.status()
        assert status["ok"] is True
        assert "ts" in status
