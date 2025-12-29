"""Pytest configuration and fixtures for CLI tests.

This conftest.py ensures tests work for both developers (editable install)
and users (pip installed package).
"""

import json
import os
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner


def pytest_configure(config):
    """Configure pytest with custom markers and path setup."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


@pytest.fixture(scope="session", autouse=True)
def setup_test_path():
    """Ensure the package root is in the Python path.

    This makes the package importable whether tests are run from:
    - The package directory (packages/cli)
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


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_agent_module(tmp_path):
    """Create a local mock agent module that can be imported."""
    # Create a mock_agent module in a unique temp location
    agent_dir = tmp_path / "mock_agent_pkg"
    agent_dir.mkdir()

    # Create __init__.py
    (agent_dir / "__init__.py").write_text("")

    # Create mock_agent.py
    mock_agent_code = '''"""Mock agent for testing."""
from typing import Dict, Any

class MockAgent:
    """A simple mock agent that echoes input."""
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": f"Processed: {payload.get('text', 'no input')}",
            "status": "success"
        }

def build_agent():
    """Factory function to build the mock agent."""
    return MockAgent()
'''
    (agent_dir / "agent.py").write_text(mock_agent_code)

    # Add to path
    if str(agent_dir.parent) not in sys.path:
        sys.path.insert(0, str(agent_dir.parent))

    return "mock_agent_pkg.agent:build_agent"


@pytest.fixture
def sample_dockfile(tmp_path, mock_agent_module):
    """Create a sample Dockfile for testing."""
    dockfile_content = f"""version: "1.0"
agent:
  name: test-agent
  description: "Test agent for CLI testing"
  entrypoint: {mock_agent_module}
  framework: langgraph
io_schema:
  input:
    type: object
    properties:
      text: {{ type: string }}
  output:
    type: object
    properties:
      result: {{ type: string }}
expose:
  port: 8080
  host: "0.0.0.0"
"""
    dockfile_path = tmp_path / "Dockfile.yaml"
    dockfile_path.write_text(dockfile_content)
    return str(dockfile_path)


@pytest.fixture
def invalid_dockfile(tmp_path):
    """Create an invalid Dockfile."""
    dockfile_path = tmp_path / "invalid.yaml"
    dockfile_path.write_text("invalid: yaml: syntax:")
    return str(dockfile_path)


@pytest.fixture
def test_payload(tmp_path):
    """Create a test payload JSON file."""
    payload = {"text": "test input"}
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(payload))
    return str(payload_file)


@pytest.fixture
def clean_env():
    """Provide a clean environment for tests that modify env vars."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
