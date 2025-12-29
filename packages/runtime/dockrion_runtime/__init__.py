"""
Dockrion Runtime Package

Provides the FastAPI runtime infrastructure for Dockrion agents.

Usage:
    from dockrion_runtime import create_app

    app = create_app(spec=my_spec, agent_entrypoint="app.graph:build")

Authentication:
    from dockrion_runtime.auth import (
        AuthContext,
        create_auth_handler,
        generate_api_key,
    )
"""

from .app import RuntimeConfig, create_app

# Re-export key auth utilities at package level
from .auth import (
    AuthContext,
    create_auth_handler,
    generate_api_key,
    is_jwt_available,
)
from .metrics import RuntimeMetrics

__version__ = "0.1.0"

__all__ = [
    # App factory
    "create_app",
    "RuntimeConfig",
    "RuntimeMetrics",
    # Auth
    "AuthContext",
    "create_auth_handler",
    "generate_api_key",
    "is_jwt_available",
]
