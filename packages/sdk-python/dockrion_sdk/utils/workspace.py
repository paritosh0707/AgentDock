"""
Workspace Utilities Module
==========================

Provides utilities for finding and working with the Dockrion workspace:
- Finding the workspace root (monorepo detection)
- Calculating relative paths for agents
- Detecting local Dockrion packages for development builds
"""

from pathlib import Path
from typing import List, Optional

from dockrion_common.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# Constants
# ============================================================================

# Dockrion packages that should be installed in Docker (in dependency order)
DOCKRION_PACKAGES = [
    ("dockrion-common", "common-py"),
    ("dockrion-schema", "schema"),
    ("dockrion-adapters", "adapters"),
    ("dockrion-policy", "policy-engine"),
    ("dockrion-telemetry", "telemetry"),
    ("dockrion-runtime", "runtime"),
]


# ============================================================================
# Workspace Detection
# ============================================================================


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


# ============================================================================
# Package Detection
# ============================================================================


def detect_local_packages(workspace_root: Path) -> Optional[List[dict]]:
    """
    Detect local Dockrion packages in the workspace for development builds.

    Scans the workspace's packages/ directory for valid Python packages
    (those with pyproject.toml or setup.py) that match known Dockrion packages.

    Args:
        workspace_root: Root of the workspace/monorepo

    Returns:
        List of package dicts with 'name' and 'path' keys, or None if not found.
        Example: [{"name": "common-py", "path": "packages/common-py"}, ...]
    """
    packages_dir = workspace_root / "packages"
    if not packages_dir.exists():
        return None

    local_packages = []
    for pkg_name, dir_name in DOCKRION_PACKAGES:
        pkg_path = packages_dir / dir_name
        # Check if it's a valid Python package (has pyproject.toml or setup.py)
        if pkg_path.exists() and (
            (pkg_path / "pyproject.toml").exists() or (pkg_path / "setup.py").exists()
        ):
            local_packages.append({
                "name": dir_name,
                "path": f"packages/{dir_name}",  # Relative to workspace root
            })
            logger.debug(f"Found local package: {pkg_name} at packages/{dir_name}")

    return local_packages if local_packages else None


__all__ = [
    "find_workspace_root",
    "get_relative_agent_path",
    "detect_local_packages",
    "DOCKRION_PACKAGES",
]
