"""
Workspace Utilities Module
==========================

Provides utilities for finding and working with the Dockrion workspace:
- Finding the workspace root (monorepo detection)
- Calculating relative paths for agents
"""

from pathlib import Path
from typing import Optional


def find_workspace_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the workspace root containing the packages/ directory.

    Walks up the directory tree from start_path looking for a directory
    that contains 'packages/common-py' (indicating the Dockrion monorepo root).

    Args:
        start_path: Starting directory (defaults to current working directory)

    Returns:
        Path to workspace root, or None if not found
    """
    current = start_path or Path.cwd()

    # Walk up directory tree looking for packages/
    for parent in [current] + list(current.parents):
        packages_dir = parent / "packages" / "common-py"
        if packages_dir.exists():
            return parent

    return None


def get_relative_agent_path(workspace_root: Path, agent_dir: Path) -> str:
    """
    Get the relative path from workspace root to agent directory.

    Args:
        workspace_root: The workspace root directory
        agent_dir: The agent's directory

    Returns:
        Relative path string (e.g., 'examples/invoice_copilot')
    """
    try:
        return str(agent_dir.relative_to(workspace_root))
    except ValueError:
        # agent_dir is not under workspace_root
        return "."


__all__ = [
    "find_workspace_root",
    "get_relative_agent_path",
]
