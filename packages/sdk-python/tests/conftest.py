"""Pytest configuration and fixtures for SDK tests."""
import os
import pytest
from pathlib import Path


@pytest.fixture
def sample_dockfile(tmp_path):
    """Create a sample Dockfile for testing."""
    dockfile_content = """
version: "1.0"
agent:
  name: test-agent
  description: "Test agent for SDK testing"
  entrypoint: tests.fixtures.mock_agent:build_agent
  framework: langgraph
model:
  provider: openai
  name: gpt-4o-mini
  temperature: 0.2
  max_tokens: 1500
io_schema:
  input:
    type: object
    properties:
      text: { type: string }
  output:
    type: object
    properties:
      result: { type: string }
expose:
  port: 8080
  host: "0.0.0.0"
"""
    dockfile_path = tmp_path / "Dockfile.yaml"
    dockfile_path.write_text(dockfile_content.strip())
    return str(dockfile_path)


@pytest.fixture
def invalid_yaml_dockfile(tmp_path):
    """Create a Dockfile with invalid YAML."""
    invalid_content = """
version: "1.0"
agent:
  name: test-agent
  entrypoint: invalid:entrypoint
  framework: langgraph
  invalid_indentation
model:
  provider: openai
"""
    dockfile_path = tmp_path / "invalid.yaml"
    dockfile_path.write_text(invalid_content)
    return str(dockfile_path)


@pytest.fixture
def dockfile_with_env_vars(tmp_path):
    """Create a Dockfile with environment variables."""
    content = """
version: "1.0"
agent:
  name: test-agent
  entrypoint: tests.fixtures.mock_agent:build_agent
  framework: langgraph
model:
  provider: openai
  name: ${MODEL_NAME:-gpt-4o-mini}
io_schema:
  input:
    type: object
    properties:
      text: { type: string }
  output:
    type: object
    properties:
      result: { type: string }
expose:
  port: 8080
  host: "0.0.0.0"
"""
    dockfile_path = tmp_path / "Dockfile.yaml"
    dockfile_path.write_text(content.strip())
    return str(dockfile_path)


@pytest.fixture
def set_env_vars():
    """Set test environment variables."""
    original_env = os.environ.copy()
    os.environ["MODEL_NAME"] = "test-model"
    os.environ["OPENAI_API_KEY"] = "test-key-123"
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def runtime_dir(tmp_path):
    """Create a temporary runtime directory."""
    runtime_path = tmp_path / ".dockrion_runtime"
    runtime_path.mkdir()
    return runtime_path

