"""
Utilities Module
================

Shared utilities for the Dockrion SDK:
- Workspace/monorepo detection
- Package manager utilities (uv/pip)
"""

from .package_manager import (
    check_uv_available,
    install_requirements,
    print_uv_setup_instructions,
)
from .workspace import find_workspace_root, get_relative_agent_path

__all__ = [
    "find_workspace_root",
    "get_relative_agent_path",
    "check_uv_available",
    "print_uv_setup_instructions",
    "install_requirements",
]
