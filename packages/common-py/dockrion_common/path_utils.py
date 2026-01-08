"""
Path utilities for module resolution.

This module provides utilities for resolving Python module paths,
particularly for dynamically loading agent handlers and entrypoints.
"""

import sys
from pathlib import Path


def resolve_module_path(module_path: str, base_dir: Path, max_levels: int = 5) -> Path:
    """
    Resolve the project root directory for a given module path.

    This function walks up the directory tree from base_dir to find where
    the top-level module of module_path actually exists. This is necessary
    for importing modules that may be nested in subdirectories.

    Supports both package directories and single-file modules:
    - Package: module/ directory (with or without __init__.py)
    - Single file: module.py file

    Follows Python's import semantics: when both module/ and module.py exist,
    the package (directory) takes precedence.

    Args:
        module_path: Module path in format "module.submodule:callable" or "module.submodule"
                    Examples: "app.service:handler", "myapp.agents:create_agent",
                              "agent:run" (single file)
        base_dir: Starting directory to search from (typically Dockfile directory)
        max_levels: Maximum number of parent directories to search (safety limit)

    Returns:
        Path to the directory containing the top-level module

    Examples:
        >>> # For "app.service:handler" with base_dir="/project/examples/agent1"
        >>> # If "app" exists at "/project/examples/agent1/app", returns that path
        >>> resolve_module_path("app.service:handler", Path("/project/examples/agent1"))
        Path("/project/examples/agent1")

        >>> # If "app" exists at "/project/app", walks up and returns that
        >>> resolve_module_path("app.service:handler", Path("/project/examples/agent1"))
        Path("/project")

        >>> # For single-file module "agent:run" with agent.py
        >>> resolve_module_path("agent:run", Path("/project"))
        Path("/project")
    """
    # Extract the top-level module name
    # "app.service:handler" -> "app.service" -> "app"
    handler_module = module_path.split(":")[0]  # Remove callable part if present
    top_level_module = handler_module.split(".")[0]  # Get first part

    # Start from base_dir and walk up to find the module
    project_root = base_dir
    for _ in range(max_levels):
        pkg_path = project_root / top_level_module
        file_path = project_root / f"{top_level_module}.py"

        # Check for package first (Python semantics: package takes precedence)
        if pkg_path.is_dir():
            return project_root

        # Check for single-file module
        if file_path.is_file():
            return project_root

        # Check if we've reached the filesystem root
        if project_root.parent == project_root:
            break

        # Move up one level
        project_root = project_root.parent

    # If not found after walking up, return the original base_dir
    # (module might be installed in site-packages or PYTHONPATH)
    return base_dir


def add_to_python_path(path: Path) -> bool:
    """
    Add a directory to Python's sys.path if not already present.

    Args:
        path: Directory path to add to sys.path

    Returns:
        True if path was added, False if it was already in sys.path

    Examples:
        >>> add_to_python_path(Path("/my/project"))
        True  # Added to sys.path
        >>> add_to_python_path(Path("/my/project"))
        False  # Already in sys.path
    """
    path_str = str(path.resolve())
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
        return True
    return False


def setup_module_path(module_path: str, base_dir: Path, max_levels: int = 5) -> Path:
    """
    Resolve and add module path to Python's sys.path.

    This is a convenience function that combines resolve_module_path()
    and add_to_python_path() for the common use case of setting up
    the Python path before importing a module.

    Args:
        module_path: Module path in format "module.submodule:callable"
        base_dir: Starting directory to search from
        max_levels: Maximum number of parent directories to search

    Returns:
        Path that was added to sys.path

    Examples:
        >>> # Setup path for importing "app.service:handler"
        >>> project_root = setup_module_path(
        ...     "app.service:handler",
        ...     Path("/project/examples/agent1")
        ... )
        >>> # Now you can import app.service
        >>> import app.service
    """
    project_root = resolve_module_path(module_path, base_dir, max_levels)
    add_to_python_path(project_root)
    return project_root
