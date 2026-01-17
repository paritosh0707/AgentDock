"""
Dockrion Build System
=====================

Provides utilities for resolving what files and directories
should be included in Docker builds:

- Module detection (file vs package)
- Import auto-detection (AST-based)
- Glob pattern resolution
- Build resolution with conflict handling

Usage:
    from dockrion_sdk.build import BuildResolver, BuildResolution
    from dockrion_sdk.build import detect_module_type, ModuleType, ModuleInfo

    resolver = BuildResolver(spec, project_root)
    resolution = resolver.resolve()

    print(resolution.directories)  # Directories to copy
    print(resolution.files)        # Files to copy
    print(resolution.warnings)     # Any warnings
"""

from .import_detector import detect_local_imports, find_entry_file
from .module_detector import ModuleInfo, ModuleType, detect_module_type, resolve_entrypoint_modules
from .pattern_resolver import matches_pattern, resolve_glob_patterns
from .resolver import BuildResolution, BuildResolver

__all__ = [
    # Module detection
    "ModuleType",
    "ModuleInfo",
    "detect_module_type",
    "resolve_entrypoint_modules",
    # Pattern resolution
    "resolve_glob_patterns",
    "matches_pattern",
    # Import detection
    "detect_local_imports",
    "find_entry_file",
    # Build resolution
    "BuildResolver",
    "BuildResolution",
]
