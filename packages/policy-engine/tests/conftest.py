"""Pytest configuration and fixtures for policy-engine tests.

This conftest.py ensures tests work for both developers (editable install)
and users (pip installed package).
"""

import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers and path setup."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_path():
    """Ensure the package root is in the Python path.

    This makes the package importable whether tests are run from:
    - The package directory (packages/policy-engine)
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
def sample_tool_policy():
    """Create a sample tool policy for testing."""
    return {"allowed": ["web_search", "calculator"], "deny_by_default": True}


@pytest.fixture
def sample_safety_policy():
    """Create a sample safety policy for testing."""
    return {
        "redact_patterns": [r"\b\d{16}\b", r"\b\d{3}-\d{2}-\d{4}\b"],
        "max_output_chars": 5000,
        "block_prompt_injection": True,
    }
