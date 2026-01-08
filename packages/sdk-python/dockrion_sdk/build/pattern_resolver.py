"""
Pattern Resolution for Build System
====================================

Provides utilities for resolving glob patterns to actual files/directories
and checking if paths match exclude patterns.
"""

import fnmatch
from pathlib import Path
from typing import List, Set, Tuple

from dockrion_common.logger import get_logger

logger = get_logger(__name__)


def resolve_glob_patterns(
    patterns: List[str],
    project_root: Path,
) -> Tuple[List[str], List[str]]:
    """
    Resolve glob patterns to actual files and directories.

    Args:
        patterns: List of glob patterns (e.g., "*.json", "data/**")
        project_root: Root directory to search from

    Returns:
        Tuple of (directories, files) that match the patterns

    Examples:
        >>> dirs, files = resolve_glob_patterns(["*.json", "data/**"], Path("/project"))
        >>> files
        ['config.json', 'data/input.txt', 'data/output.json']
    """
    matched_dirs: Set[str] = set()
    matched_files: Set[str] = set()

    for pattern in patterns:
        # Normalize pattern - remove leading ** or /
        normalized_pattern = pattern.lstrip("*").lstrip("/")
        if not normalized_pattern:
            normalized_pattern = pattern

        try:
            # Use rglob for recursive patterns, glob for non-recursive
            if "**" in pattern:
                # Remove ** prefix for rglob
                search_pattern = pattern.replace("**/", "").replace("**", "*")
                matches = list(project_root.rglob(search_pattern))
            else:
                matches = list(project_root.glob(pattern))

            for path in matches:
                # Skip hidden files and directories
                if any(part.startswith(".") for part in path.parts):
                    continue

                # Get relative path from project root
                try:
                    rel_path = path.relative_to(project_root)
                    rel_path_str = str(rel_path).replace("\\", "/")

                    if path.is_dir():
                        matched_dirs.add(rel_path_str)
                    elif path.is_file():
                        matched_files.add(rel_path_str)
                except ValueError:
                    # Path is not relative to project_root
                    continue

        except Exception as e:
            logger.warning(f"Error resolving pattern '{pattern}': {e}")

    return sorted(matched_dirs), sorted(matched_files)


def matches_pattern(path: str, patterns: List[str]) -> bool:
    """
    Check if a path matches any of the given patterns.

    Supports:
    - Exact matches: "tests" matches "tests"
    - Glob patterns: "*.pyc" matches "module.pyc"
    - Recursive patterns: "**/__pycache__" matches "app/__pycache__"

    Args:
        path: Path to check (relative to project root)
        patterns: List of patterns to match against

    Returns:
        True if path matches any pattern

    Examples:
        >>> matches_pattern("tests", ["tests/", "**/__pycache__"])
        True

        >>> matches_pattern("app/__pycache__", ["tests/", "**/__pycache__"])
        True

        >>> matches_pattern("app/main.py", ["tests/", "**/__pycache__"])
        False
    """
    # Normalize path separators
    normalized_path = path.replace("\\", "/").rstrip("/")

    for pattern in patterns:
        original_pattern = pattern.replace("\\", "/")
        normalized_pattern = original_pattern.rstrip("/")

        # Exact match
        if normalized_pattern == normalized_path:
            return True

        # Check if path starts with pattern (for directory patterns like "tests/")
        # A pattern "tests/" should match "tests/unit", "tests/integration", etc.
        if original_pattern.endswith("/"):
            # Pattern is a directory, check if path is inside it
            if normalized_path.startswith(normalized_pattern + "/"):
                return True
            # Also match exact directory name
            if normalized_path == normalized_pattern:
                return True

        # Glob pattern matching
        if fnmatch.fnmatch(normalized_path, normalized_pattern):
            return True

        # Handle ** patterns manually for better matching
        if "**" in normalized_pattern:
            # Convert ** to a regex-like pattern for fnmatch
            # **/ at start means "anywhere"
            if normalized_pattern.startswith("**/"):
                suffix = normalized_pattern[3:]  # Remove **/
                # Check if the path ends with or contains the suffix
                if fnmatch.fnmatch(normalized_path, f"*/{suffix}") or fnmatch.fnmatch(
                    normalized_path, suffix
                ):
                    return True
                # Also check each path component
                path_parts = normalized_path.split("/")
                for i in range(len(path_parts)):
                    remaining = "/".join(path_parts[i:])
                    if fnmatch.fnmatch(remaining, suffix):
                        return True

    return False


def filter_by_excludes(
    items: Set[str],
    exclude_patterns: List[str],
) -> List[str]:
    """
    Filter a set of items by exclude patterns.

    Args:
        items: Set of paths to filter
        exclude_patterns: Patterns to exclude

    Returns:
        Sorted list of items that don't match any exclude pattern

    Examples:
        >>> items = {"app", "tests", "utils"}
        >>> filter_by_excludes(items, ["tests/"])
        ['app', 'utils']
    """
    return sorted(item for item in items if not matches_pattern(item, exclude_patterns))

