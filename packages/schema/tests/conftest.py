"""Pytest configuration and fixtures for schema tests.

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
    config.addinivalue_line("markers", "requires_yaml: marks tests that require pyyaml")


@pytest.fixture(scope="session", autouse=True)
def setup_test_path():
    """Ensure the package root is in the Python path.

    This makes the package importable whether tests are run from:
    - The package directory (packages/schema)
    - The project root (Dockrion)
    - Or after pip install
    """
    package_root = Path(__file__).parent.parent

    # Add package root to path for local development
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)

    yield


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle optional dependencies."""
    try:
        import yaml

        has_yaml = True
    except ImportError:
        has_yaml = False

    for item in items:
        # Skip tests marked as requires_yaml if yaml is not installed
        if "requires_yaml" in item.keywords and not has_yaml:
            item.add_marker(pytest.mark.skip(reason="pyyaml not installed"))


@pytest.fixture
def minimal_valid_dockfile():
    """Minimal valid Dockfile configuration"""
    return {
        "version": "1.0",
        "agent": {
            "name": "test-agent",
            "entrypoint": "app.main:build_graph",
            "framework": "langgraph",
        },
        "io_schema": {},
        "expose": {"port": 8080},
    }


@pytest.fixture
def full_valid_dockfile():
    """Full Dockfile with all optional fields"""
    return {
        "version": "1.0",
        "agent": {
            "name": "invoice-copilot",
            "description": "Extracts data from invoices",
            "entrypoint": "examples.invoice_copilot.app.graph:build_graph",
            "framework": "langgraph",
        },
        "io_schema": {
            "input": {
                "type": "object",
                "properties": {
                    "document_text": {"type": "string"},
                    "currency_hint": {"type": "string"},
                },
                "required": ["document_text"],
            },
            "output": {
                "type": "object",
                "properties": {"vendor": {"type": "string"}, "total": {"type": "number"}},
            },
        },
        "arguments": {"max_retries": 3, "timeout": 30},
        "policies": {
            "tools": {"allowed": ["extract_invoice", "summarize"], "deny_by_default": True},
            "safety": {
                "redact_patterns": [r"\b\d{16}\b"],
                "max_output_chars": 5000,
                "block_prompt_injection": True,
            },
        },
        "auth": {
            "mode": "api_key",
            "api_keys": {"enabled": True, "rotation_days": 30},
            "roles": [{"name": "admin", "permissions": ["deploy", "invoke", "view_metrics"]}],
            "rate_limits": {"admin": "1000/m", "viewer": "60/m"},
        },
        "observability": {
            "tracing": True,
            "log_level": "info",
            "metrics": {"latency": True, "tokens": True, "cost": True},
        },
        "expose": {
            "rest": True,
            "streaming": "sse",
            "port": 8080,
            "host": "0.0.0.0",
            "cors": {"origins": ["http://localhost:3000"], "methods": ["GET", "POST"]},
        },
        "metadata": {
            "maintainer": "alice@example.com",
            "version": "1.0.0",
            "tags": ["invoice", "extraction", "production"],
        },
    }
