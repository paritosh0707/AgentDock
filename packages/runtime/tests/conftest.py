"""Pytest configuration and fixtures for runtime tests.

This conftest.py ensures tests work for both developers (editable install)
and users (pip installed package).
"""

import sys
from pathlib import Path

import pytest

# Enable pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """Configure pytest with custom markers and path setup."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "requires_events: marks tests that require events package")


@pytest.fixture(scope="session", autouse=True)
def setup_test_path():
    """Ensure the package root is in the Python path.

    This makes the package importable whether tests are run from:
    - The package directory (packages/runtime)
    - The project root (Dockrion)
    - Or after pip install
    """
    package_root = Path(__file__).parent.parent

    # Add package root to path for local development
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)

    yield


@pytest.fixture
def sample_dockspec():
    """Create a sample DockSpec for testing."""
    return {
        "version": "1.0",
        "agent": {
            "name": "test-agent",
            "entrypoint": "app.main:build_graph",
            "framework": "langgraph",
        },
        "io_schema": {
            "input": {"type": "object", "properties": {"text": {"type": "string"}}},
            "output": {"type": "object", "properties": {"result": {"type": "string"}}},
        },
        "expose": {"port": 8080, "host": "0.0.0.0"},
    }


@pytest.fixture
def sample_dockspec_with_auth(sample_dockspec):
    """Create a sample DockSpec with auth config."""
    sample_dockspec["auth"] = {
        "mode": "api_key",
        "api_keys": {"enabled": True},
        "rate_limits": {"default": "100/m"},
    }
    return sample_dockspec
