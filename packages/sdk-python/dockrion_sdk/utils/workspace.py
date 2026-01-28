"""
Workspace Utilities Module
==========================

Provides utilities for finding and working with the Dockrion workspace:
- Finding the workspace root (monorepo detection)
- Calculating relative paths for agents
- Reading dependency versions from pyproject.toml (single source of truth)
"""

import re
import tomllib  # Python 3.11+ built-in
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

from dockrion_common.logger import get_logger

logger = get_logger(__name__)

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
# PyProject.toml Utilities - Single Source of Truth for Versions
# ============================================================================


def _parse_version_constraint(dep_string: str) -> Tuple[str, str]:
    """
    Parse a dependency string like 'pydantic>=2.5' into (name, constraint).

    Handles various formats:
    - 'pydantic>=2.5'
    - 'uvicorn[standard]>=0.27.0'
    - 'PyJWT[crypto]>=2.8.0'

    Returns:
        Tuple of (package_name_normalized, version_constraint)
    """
    # Match patterns like: package>=1.0, package[extra]>=1.0, package==1.0
    match = re.match(r"^([a-zA-Z0-9_-]+)(?:\[[^\]]+\])?(.*)", dep_string)
    if match:
        name = match.group(1).lower().replace("_", "-")
        constraint = match.group(2).strip() or ""
        return name, constraint
    return dep_string.lower(), ""


@lru_cache(maxsize=1)
def get_dockrion_pyproject() -> dict:
    """
    Load and cache the main dockrion pyproject.toml.

    This is the single source of truth for dockrion's dependency versions.
    Uses find_workspace_root() to locate the pyproject.toml.

    Returns:
        Parsed pyproject.toml as dict, or empty dict if not found
    """
    workspace = find_workspace_root()
    if not workspace:
        logger.debug("Workspace root not found, pyproject.toml unavailable")
        return {}

    pyproject_path = workspace / "packages" / "dockrion" / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)
                logger.debug(f"Loaded pyproject.toml from {pyproject_path}")
                return config
        except Exception as e:
            logger.warning(f"Failed to parse pyproject.toml: {e}")
            return {}
    return {}


@lru_cache(maxsize=1)
def get_runtime_pyproject() -> dict:
    """
    Load and cache the runtime pyproject.toml.

    Returns:
        Parsed pyproject.toml as dict, or empty dict if not found
    """
    workspace = find_workspace_root()
    if not workspace:
        return {}

    pyproject_path = workspace / "packages" / "runtime" / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            logger.warning(f"Failed to parse runtime pyproject.toml: {e}")
            return {}
    return {}


def get_dockrion_version() -> str:
    """
    Get the current dockrion version from pyproject.toml.

    Returns:
        Version string (e.g., '0.0.2'), or '0.0.1' as fallback
    """
    config = get_dockrion_pyproject()
    return config.get("project", {}).get("version", "0.0.1")


def get_core_dependencies_from_pyproject() -> Dict[str, str]:
    """
    Get core dependencies from dockrion's pyproject.toml [project.dependencies].

    These are the base dependencies required for dockrion to function.

    Returns:
        Dict mapping package name to version constraint
        Example: {'pydantic': '>=2.5', 'typer': '>=0.12.0'}
    """
    config = get_dockrion_pyproject()
    deps = config.get("project", {}).get("dependencies", [])

    result: Dict[str, str] = {}
    for dep in deps:
        name, constraint = _parse_version_constraint(dep)
        result[name] = constraint
    return result


def get_runtime_dependencies_from_pyproject() -> Dict[str, str]:
    """
    Get runtime dependencies from dockrion's [project.optional-dependencies.runtime].

    These are dependencies needed when running agents (fastapi, uvicorn, etc.).

    Returns:
        Dict mapping package name to version constraint
    """
    config = get_dockrion_pyproject()
    optional = config.get("project", {}).get("optional-dependencies", {})
    runtime_deps = optional.get("runtime", [])

    result: Dict[str, str] = {}
    for dep in runtime_deps:
        name, constraint = _parse_version_constraint(dep)
        result[name] = constraint

    # Also get httpx and aiohttp from runtime package dev dependencies
    runtime_config = get_runtime_pyproject()
    runtime_deps_list = runtime_config.get("project", {}).get("dependencies", [])
    for dep in runtime_deps_list:
        if "httpx" in dep.lower() or "aiohttp" in dep.lower():
            name, constraint = _parse_version_constraint(dep)
            if name not in result:  # Don't override if already set
                result[name] = constraint

    return result


def get_framework_dependencies_from_pyproject(framework: str) -> Dict[str, str]:
    """
    Get framework-specific dependencies from dockrion's optional-dependencies.

    Args:
        framework: Framework name (e.g., 'langgraph', 'langchain')

    Returns:
        Dict mapping package name to version constraint
    """
    config = get_dockrion_pyproject()
    optional = config.get("project", {}).get("optional-dependencies", {})
    framework_deps = optional.get(framework.lower(), [])

    result: Dict[str, str] = {}
    for dep in framework_deps:
        name, constraint = _parse_version_constraint(dep)
        result[name] = constraint
    return result


def clear_pyproject_cache() -> None:
    """
    Clear the cached pyproject.toml data.

    Useful for testing or when pyproject.toml files have been modified.
    """
    get_dockrion_pyproject.cache_clear()
    get_runtime_pyproject.cache_clear()


__all__ = [
    # Workspace detection
    "find_workspace_root",
    "get_relative_agent_path",
    # PyProject.toml utilities (single source of truth)
    "get_dockrion_pyproject",
    "get_runtime_pyproject",
    "get_dockrion_version",
    "get_core_dependencies_from_pyproject",
    "get_runtime_dependencies_from_pyproject",
    "get_framework_dependencies_from_pyproject",
    "clear_pyproject_cache",
]
