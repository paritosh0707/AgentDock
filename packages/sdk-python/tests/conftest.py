"""Pytest configuration and fixtures for SDK tests.

This conftest.py ensures tests work for both developers (editable install)
and users (pip installed package).
"""

import os
import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers and path setup."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "requires_docker: marks tests that require docker")


@pytest.fixture(scope="session", autouse=True)
def setup_test_path():
    """Ensure the package root and tests directory are in the Python path.

    This makes fixtures importable whether tests are run from:
    - The package directory (packages/sdk-python)
    - The project root (Dockrion)
    - Or after pip install
    """
    package_root = Path(__file__).parent.parent
    tests_root = Path(__file__).parent

    # Add package root to path for local development
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)

    # Add tests directory for fixture imports
    tests_root_str = str(tests_root)
    if tests_root_str not in sys.path:
        sys.path.insert(0, tests_root_str)

    yield


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle optional dependencies and conditions."""
    import subprocess

    # Check if Docker is available
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
        has_docker = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        has_docker = False

    for item in items:
        # Skip tests marked as requires_docker if docker is not available
        if "requires_docker" in item.keywords and not has_docker:
            item.add_marker(pytest.mark.skip(reason="Docker not available"))


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
io_schema: {}
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


@pytest.fixture
def clean_env():
    """Provide a clean environment for tests that modify env vars."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
