"""Pytest configuration and fixtures for telemetry tests.

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
    - The package directory (packages/telemetry)
    - The project root (Dockrion)
    - Or after pip install
    """
    package_root = Path(__file__).parent.parent

    # Add package root to path for local development
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)

    yield
