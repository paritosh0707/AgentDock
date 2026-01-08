"""
Module Detection for Build System
==================================

Provides utilities for detecting Python module types (package vs file)
and resolving entrypoints to files/directories for Docker builds.

Follows Python's import semantics:
- Package (directory) takes precedence over file when both exist
- Supports namespace packages (PEP 420)
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from dockrion_common.logger import get_logger

logger = get_logger(__name__)


class ModuleType(Enum):
    """Type of Python module."""

    PACKAGE = "package"
    """Directory with __init__.py"""

    FILE = "file"
    """Single .py file"""

    NAMESPACE = "namespace"
    """Directory without __init__.py (PEP 420)"""

    AMBIGUOUS = "ambiguous"
    """Both file and package exist"""

    NOT_FOUND = "not_found"
    """Neither file nor package exists"""


@dataclass
class ModuleInfo:
    """Information about a detected module."""

    name: str
    """Module name (e.g., 'app', 'utils')"""

    type: ModuleType
    """Detected module type"""

    path: Path
    """Path to the module (file or directory)"""

    warning: Optional[str] = None
    """Optional warning message about the module"""


def detect_module_type(module_name: str, parent_dir: Path) -> ModuleInfo:
    """
    Detect whether a module is a package, file, or ambiguous.

    Follows Python's import semantics:
    - Package (directory) takes precedence over file
    - Warns if both exist (bad practice)

    Args:
        module_name: The module name (e.g., "app", "utils")
        parent_dir: Directory containing the module

    Returns:
        ModuleInfo with type and optional warning

    Examples:
        >>> info = detect_module_type("app", Path("/project"))
        >>> info.type
        ModuleType.PACKAGE  # if app/ exists with __init__.py

        >>> info = detect_module_type("agent", Path("/project"))
        >>> info.type
        ModuleType.FILE  # if only agent.py exists
    """
    dir_path = parent_dir / module_name
    file_path = parent_dir / f"{module_name}.py"
    init_path = dir_path / "__init__.py"

    dir_exists = dir_path.is_dir()
    file_exists = file_path.is_file()
    has_init = init_path.is_file() if dir_exists else False

    # Case 1: Both exist - ambiguous (package wins, but warn)
    if dir_exists and file_exists:
        return ModuleInfo(
            name=module_name,
            type=ModuleType.AMBIGUOUS,
            path=dir_path,  # Package takes precedence
            warning=(
                f"Both '{module_name}.py' and '{module_name}/' exist. "
                f"Python will import the package ('{module_name}/'), "
                f"not the file. Consider renaming one to avoid confusion."
            ),
        )

    # Case 2: Package (directory with __init__.py)
    if dir_exists and has_init:
        return ModuleInfo(
            name=module_name,
            type=ModuleType.PACKAGE,
            path=dir_path,
        )

    # Case 3: Namespace package (directory without __init__.py - PEP 420)
    if dir_exists and not has_init:
        return ModuleInfo(
            name=module_name,
            type=ModuleType.NAMESPACE,
            path=dir_path,
            warning=(
                f"'{module_name}/' is a namespace package (no __init__.py). "
                f"This is valid but may cause import issues in some cases."
            ),
        )

    # Case 4: Single file module
    if file_exists:
        return ModuleInfo(
            name=module_name,
            type=ModuleType.FILE,
            path=file_path,
        )

    # Case 5: Not found
    return ModuleInfo(
        name=module_name,
        type=ModuleType.NOT_FOUND,
        path=parent_dir / module_name,
        warning=f"Module '{module_name}' not found in {parent_dir}",
    )


def resolve_entrypoint_modules(
    entrypoint: str,
    project_root: Path,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Resolve an entrypoint to directories and files to copy.

    Args:
        entrypoint: Format "module.path:callable" (e.g., "src.app:build_agent")
        project_root: Root directory of the project

    Returns:
        Tuple of (directories, files, warnings)

    Examples:
        >>> dirs, files, warns = resolve_entrypoint_modules("src.app:func", Path("/project"))
        >>> dirs
        ['src']  # Copy src/ directory

        >>> dirs, files, warns = resolve_entrypoint_modules("agent:func", Path("/project"))
        >>> # If agent.py exists: ([], ['agent.py'], [])
        >>> # If agent/ exists: (['agent'], [], [])
    """
    directories: List[str] = []
    files: List[str] = []
    warnings: List[str] = []

    if ":" not in entrypoint:
        warnings.append(f"Invalid entrypoint format: {entrypoint}")
        return directories, files, warnings

    module_path = entrypoint.rsplit(":", 1)[0]
    parts = module_path.split(".")

    if len(parts) == 1:
        # Single-level: could be file or package
        # e.g., "agent:func" or "app:build_agent"
        module_name = parts[0]
        info = detect_module_type(module_name, project_root)

        if info.warning:
            warnings.append(info.warning)

        if info.type in (ModuleType.PACKAGE, ModuleType.NAMESPACE, ModuleType.AMBIGUOUS):
            directories.append(module_name)
        elif info.type == ModuleType.FILE:
            files.append(f"{module_name}.py")
        else:
            # NOT_FOUND - assume directory for backward compatibility
            directories.append(module_name)
            logger.warning(f"Module '{module_name}' not found, assuming directory")

    else:
        # Multi-level: always a package structure
        # e.g., "src.app:func" or "mypackage.submodule:handler"
        top_module = parts[0]

        # Top level must be a directory
        info = detect_module_type(top_module, project_root)

        if info.warning:
            warnings.append(info.warning)

        if info.type == ModuleType.FILE:
            # Error: Can't have dots if top level is a file
            warnings.append(
                f"Invalid entrypoint: '{module_path}' has dots but "
                f"'{top_module}' is a file, not a package. "
                f"Use '{top_module}:callable' for single-file modules."
            )

        directories.append(top_module)

        # Optionally validate the nested module exists
        nested_path = project_root / "/".join(parts[:-1])
        final_module = parts[-1]

        if nested_path.exists():
            nested_info = detect_module_type(final_module, nested_path)
            if nested_info.warning and nested_info.type == ModuleType.AMBIGUOUS:
                warnings.append(nested_info.warning)

    return directories, files, warnings

