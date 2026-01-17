"""
Import Detection for Build System
==================================

Provides AST-based detection of local imports in Python files.
Used for auto-detecting dependencies that need to be included
in Docker builds.
"""

import ast
from pathlib import Path
from typing import Optional, Set, Tuple

from dockrion_common.logger import get_logger

from .module_detector import ModuleType, detect_module_type

logger = get_logger(__name__)


def find_entry_file(module_path: str, project_root: Path) -> Optional[Path]:
    """
    Find the Python file for a module path.

    Args:
        module_path: Module path (e.g., "app.main", "agent")
        project_root: Root directory to search from

    Returns:
        Path to the Python file if found, None otherwise

    Examples:
        >>> find_entry_file("app.main", Path("/project"))
        Path("/project/app/main.py")

        >>> find_entry_file("agent", Path("/project"))
        Path("/project/agent.py")  # or Path("/project/agent/__init__.py")
    """
    parts = module_path.split(".")

    if len(parts) == 1:
        # Single module - could be file or package
        module_name = parts[0]

        # Check for single file first
        file_path = project_root / f"{module_name}.py"
        if file_path.is_file():
            return file_path

        # Check for package __init__.py
        init_path = project_root / module_name / "__init__.py"
        if init_path.is_file():
            return init_path

    else:
        # Multi-part path
        base_path = project_root / "/".join(parts[:-1])
        final_module = parts[-1]

        # Check for module file
        module_file = base_path / f"{final_module}.py"
        if module_file.is_file():
            return module_file

        # Check for package __init__.py
        package_init = base_path / final_module / "__init__.py"
        if package_init.is_file():
            return package_init

    return None


def detect_local_imports(
    entry_file: Path,
    project_root: Path,
    visited: Optional[Set[Path]] = None,
) -> Tuple[Set[str], Set[str]]:
    """
    Parse a Python file and detect local imports recursively.

    Uses Python's AST module to find import statements and determine
    which ones refer to local modules (not installed packages).

    Handles circular imports by tracking visited files.

    Args:
        entry_file: Path to the Python file to analyze
        project_root: Root directory of the project
        visited: Set of already visited files (for circular import detection)

    Returns:
        Tuple of (directories, files) that are imported locally

    Examples:
        >>> dirs, files = detect_local_imports(Path("/project/app/main.py"), Path("/project"))
        >>> dirs
        {'utils', 'models'}
        >>> files
        {'helpers.py'}
    """
    if visited is None:
        visited = set()

    # Resolve to absolute path for consistent tracking
    entry_file = entry_file.resolve()

    # Check for circular imports
    if entry_file in visited:
        return set(), set()

    visited.add(entry_file)

    directories: Set[str] = set()
    files: Set[str] = set()

    # Read and parse the file
    try:
        with open(entry_file, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
    except SyntaxError as e:
        logger.warning(f"Syntax error parsing {entry_file}: {e}")
        return directories, files
    except FileNotFoundError:
        logger.warning(f"File not found: {entry_file}")
        return directories, files
    except Exception as e:
        logger.warning(f"Error reading {entry_file}: {e}")
        return directories, files

    # Extract imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                _check_and_add_module(module, project_root, directories, files)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                _check_and_add_module(module, project_root, directories, files)
            elif node.level > 0:
                # Relative import - need to resolve based on current file location
                # For now, we skip relative imports as they're within the same package
                pass

    # Recursively analyze found modules
    modules_to_analyze = list(directories) + [f.replace(".py", "") for f in files]

    for module_name in modules_to_analyze:
        # Find the entry file for this module
        module_entry = find_entry_file(module_name, project_root)
        if module_entry and module_entry not in visited:
            sub_dirs, sub_files = detect_local_imports(module_entry, project_root, visited)
            directories.update(sub_dirs)
            files.update(sub_files)

        # Also analyze all Python files in directories
        dir_path = project_root / module_name
        if dir_path.is_dir():
            for py_file in dir_path.rglob("*.py"):
                if py_file not in visited:
                    sub_dirs, sub_files = detect_local_imports(py_file, project_root, visited)
                    directories.update(sub_dirs)
                    files.update(sub_files)

    return directories, files


def _check_and_add_module(
    module_name: str,
    project_root: Path,
    directories: Set[str],
    files: Set[str],
) -> None:
    """
    Check if a module exists locally and add to appropriate set.

    Args:
        module_name: Name of the module to check
        project_root: Root directory to check in
        directories: Set to add directory modules to
        files: Set to add file modules to
    """
    # Skip common standard library and third-party modules
    # This is a heuristic - we check if the module exists locally
    info = detect_module_type(module_name, project_root)

    if info.type == ModuleType.NOT_FOUND:
        # Not a local module, skip
        return

    if info.type in (ModuleType.PACKAGE, ModuleType.NAMESPACE, ModuleType.AMBIGUOUS):
        directories.add(module_name)
    elif info.type == ModuleType.FILE:
        files.add(f"{module_name}.py")
