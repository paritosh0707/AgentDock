"""Pytest configuration and fixtures for events tests.

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
    config.addinivalue_line("markers", "requires_redis: marks tests that require redis")


@pytest.fixture(scope="session", autouse=True)
def setup_test_path():
    """Ensure the package root is in the Python path.

    This makes the package importable whether tests are run from:
    - The package directory (packages/events)
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
def sample_run_id():
    """Provide a sample run ID for testing."""
    return "test-run-12345"


@pytest.fixture
def memory_backend():
    """Create an InMemoryBackend for testing."""
    from dockrion_events import InMemoryBackend

    return InMemoryBackend()


@pytest.fixture
def event_bus(memory_backend):
    """Create an EventBus with InMemoryBackend for testing."""
    from dockrion_events import EventBus

    return EventBus(memory_backend)


@pytest.fixture
def stream_context(sample_run_id, event_bus):
    """Create a StreamContext for testing."""
    from dockrion_events import StreamContext

    return StreamContext(run_id=sample_run_id, bus=event_bus)


@pytest.fixture
def run_manager(event_bus):
    """Create a RunManager for testing."""
    from dockrion_events import RunManager

    return RunManager(event_bus)
