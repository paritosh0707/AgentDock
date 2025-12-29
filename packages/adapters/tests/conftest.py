"""Pytest configuration and fixtures for adapter tests.

This conftest.py ensures tests work for both developers (editable install)
and users (pip installed package).
"""

import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers and path setup."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "requires_langgraph: marks tests that require langgraph")


@pytest.fixture(scope="session", autouse=True)
def setup_test_path():
    """Ensure the package root and tests directory are in the Python path.

    This makes fixtures importable whether tests are run from:
    - The package directory (packages/adapters)
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

    # Cleanup (optional, but good practice)
    if package_root_str in sys.path:
        sys.path.remove(package_root_str)
    if tests_root_str in sys.path:
        sys.path.remove(tests_root_str)


@pytest.fixture
def simple_agent():
    """Create a simple test agent for testing."""
    from fixtures.sample_agents import build_simple_agent

    return build_simple_agent()


@pytest.fixture
def echo_agent():
    """Create an echo test agent for testing."""
    from fixtures.sample_agents import build_echo_agent

    return build_echo_agent()


@pytest.fixture
def stateful_agent():
    """Create a stateful agent for testing."""
    from fixtures.sample_agents import build_stateful_agent

    return build_stateful_agent()


@pytest.fixture
def config_agent():
    """Create a config-supporting agent for testing."""
    from fixtures.sample_agents import build_config_agent

    return build_config_agent()


@pytest.fixture
def streaming_agent():
    """Create a streaming agent for testing."""
    from fixtures.sample_agents import build_streaming_agent

    return build_streaming_agent()


@pytest.fixture
def async_agent():
    """Create an async agent for testing."""
    from fixtures.sample_agents import build_async_agent

    return build_async_agent()


@pytest.fixture
def crashing_agent():
    """Create a crashing agent for error testing."""
    from fixtures.sample_agents import build_crashing_agent

    return build_crashing_agent()


@pytest.fixture
def invalid_output_agent():
    """Create an agent that returns invalid output."""
    from fixtures.sample_agents import build_invalid_output_agent

    return build_invalid_output_agent()


@pytest.fixture
def agent_without_invoke():
    """Create an agent without invoke method for error testing."""
    from fixtures.sample_agents import build_agent_without_invoke

    return build_agent_without_invoke()


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle optional dependencies."""
    try:
        import langgraph

        has_langgraph = True
    except ImportError:
        has_langgraph = False

    for item in items:
        # Skip tests marked as requires_langgraph if langgraph is not installed
        if "requires_langgraph" in item.keywords and not has_langgraph:
            item.add_marker(pytest.mark.skip(reason="langgraph not installed"))
