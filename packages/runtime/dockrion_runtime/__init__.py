"""
Dockrion Runtime Package

Provides the FastAPI runtime infrastructure for Dockrion agents.

Usage:
    from dockrion_runtime import create_app
    
    app = create_app(spec=my_spec, agent_entrypoint="app.graph:build")
"""

from .app import create_app, RuntimeConfig
from .metrics import RuntimeMetrics

__version__ = "0.1.0"

__all__ = [
    "create_app",
    "RuntimeConfig",
    "RuntimeMetrics",
]

