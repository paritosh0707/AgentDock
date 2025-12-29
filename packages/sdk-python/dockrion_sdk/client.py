"""
Dockrion Client Module
======================

Re-exports core client functionality for backwards compatibility.

This module provides backwards compatibility for existing code that imports from client.py.
For new code, consider importing directly from the specific modules:
- dockrion_sdk.core.loader: load_dockspec, expand_env_vars
- dockrion_sdk.core.invoker: invoke_local
- dockrion_sdk.remote.controller: ControllerClient
"""

# Re-export from core modules
from .core.invoker import invoke_local
from .core.loader import expand_env_vars, load_dockspec

# Re-export from remote module
from .remote.controller import ControllerClient

__all__ = [
    "load_dockspec",
    "expand_env_vars",
    "invoke_local",
    "ControllerClient",
]
