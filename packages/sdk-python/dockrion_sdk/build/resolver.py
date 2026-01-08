"""
Build Resolver
==============

Main build resolution system that combines:
- Entrypoint detection
- Explicit includes/excludes
- Auto-detected imports
- Conflict resolution

Produces a final list of files and directories to include in Docker builds.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from dockrion_common import BuildConflictError
from dockrion_common.logger import get_logger
from dockrion_schema import DockSpec

from .import_detector import detect_local_imports, find_entry_file
from .module_detector import resolve_entrypoint_modules
from .pattern_resolver import filter_by_excludes, matches_pattern, resolve_glob_patterns

logger = get_logger(__name__)


@dataclass
class BuildResolution:
    """Result of build include/exclude resolution."""

    directories: List[str] = field(default_factory=list)
    """Directories to copy into Docker image"""

    files: List[str] = field(default_factory=list)
    """Individual files to copy into Docker image"""

    warnings: List[str] = field(default_factory=list)
    """Warnings generated during resolution"""


class BuildResolver:
    """
    Resolves what to include in Docker builds.

    Combines:
    1. Entrypoint module (always required)
    2. Auto-detected imports (if enabled)
    3. Explicit includes from build config
    4. Exclude patterns

    Validates conflicts and produces warnings as needed.

    Example:
        >>> resolver = BuildResolver(spec, project_root)
        >>> resolution = resolver.resolve()
        >>> print(resolution.directories)
        ['app', 'utils']
        >>> print(resolution.files)
        ['config.yaml']
    """

    def __init__(self, spec: DockSpec, project_root: Path):
        """
        Initialize the build resolver.

        Args:
            spec: DockSpec containing agent and build configuration
            project_root: Root directory of the project
        """
        self.spec = spec
        self.project_root = project_root
        self.warnings: List[str] = []

    def resolve(self) -> BuildResolution:
        """
        Resolve final list of files/directories to include.

        Resolution order:
        1. Get entrypoint includes (required)
        2. Get auto-detected imports (if enabled)
        3. Get explicit includes
        4. Validate conflicts
        5. Apply excludes

        Returns:
            BuildResolution with directories, files, and warnings

        Raises:
            BuildConflictError: If critical conflicts are detected
        """
        all_dirs: Set[str] = set()
        all_files: Set[str] = set()

        # 1. Entrypoint module (required)
        ep_dirs, ep_files = self._get_entrypoint_includes()
        all_dirs.update(ep_dirs)
        all_files.update(ep_files)

        # 2. Auto-detect imports (if enabled)
        auto_dirs: Set[str] = set()
        auto_files: Set[str] = set()
        if self._is_auto_detect_enabled():
            auto_dirs, auto_files = self._get_auto_detected_imports()
            all_dirs.update(auto_dirs)
            all_files.update(auto_files)

        # 3. Explicit includes
        explicit_dirs, explicit_files = self._get_explicit_includes()
        all_dirs.update(explicit_dirs)
        all_files.update(explicit_files)

        # 4. Get exclude patterns
        excludes = self._get_exclude_patterns()

        # 5. Validate conflicts (raises errors for critical issues)
        self._validate_entrypoint_not_excluded(ep_dirs, ep_files, excludes)

        if self._is_auto_detect_enabled():
            self._validate_auto_detected_not_excluded(auto_dirs, auto_files, excludes)

        self._warn_explicit_include_conflicts(explicit_dirs, explicit_files, excludes)
        self._validate_existence(all_dirs, all_files)

        # 6. Apply excludes
        final_dirs = filter_by_excludes(all_dirs, excludes)
        final_files = filter_by_excludes(all_files, excludes)

        return BuildResolution(
            directories=final_dirs,
            files=final_files,
            warnings=self.warnings,
        )

    def _is_auto_detect_enabled(self) -> bool:
        """Check if auto-detect imports is enabled."""
        return self.spec.build is not None and self.spec.build.auto_detect_imports

    def _get_exclude_patterns(self) -> List[str]:
        """Get exclude patterns from build config."""
        if not self.spec.build:
            return []
        return self.spec.build.exclude or []

    def _get_entrypoint_includes(self) -> tuple[Set[str], Set[str]]:
        """
        Get directories and files from entrypoint/handler.

        Returns:
            Tuple of (directories, files) sets
        """
        directories: Set[str] = set()
        files: Set[str] = set()

        # Check entrypoint
        if self.spec.agent.entrypoint:
            dirs, fls, warnings = resolve_entrypoint_modules(
                self.spec.agent.entrypoint,
                self.project_root,
            )
            directories.update(dirs)
            files.update(fls)
            self.warnings.extend(warnings)

        # Check handler
        if self.spec.agent.handler:
            dirs, fls, warnings = resolve_entrypoint_modules(
                self.spec.agent.handler,
                self.project_root,
            )
            directories.update(dirs)
            files.update(fls)
            self.warnings.extend(warnings)

        return directories, files

    def _get_explicit_includes(self) -> tuple[Set[str], Set[str]]:
        """
        Get explicitly configured includes from build config.

        Returns:
            Tuple of (directories, files) sets
        """
        directories: Set[str] = set()
        files: Set[str] = set()

        if not self.spec.build or not self.spec.build.include:
            return directories, files

        include = self.spec.build.include

        # Add directories
        directories.update(include.directories)

        # Add files
        files.update(include.files)

        # Resolve patterns
        if include.patterns:
            pattern_dirs, pattern_files = resolve_glob_patterns(
                include.patterns,
                self.project_root,
            )
            directories.update(pattern_dirs)
            files.update(pattern_files)

        return directories, files

    def _get_auto_detected_imports(self) -> tuple[Set[str], Set[str]]:
        """
        Get auto-detected imports from entrypoint analysis.

        Returns:
            Tuple of (directories, files) sets
        """
        directories: Set[str] = set()
        files: Set[str] = set()

        # Get the entrypoint module path
        entrypoint = self.spec.agent.entrypoint or self.spec.agent.handler
        if not entrypoint:
            return directories, files

        # Parse module path
        module_path = entrypoint.rsplit(":", 1)[0] if ":" in entrypoint else entrypoint

        # Find the entry file
        entry_file = find_entry_file(module_path, self.project_root)
        if not entry_file:
            self.warnings.append(f"Could not find entry file for '{module_path}' to auto-detect imports")
            return directories, files

        # Detect imports
        try:
            detected_dirs, detected_files = detect_local_imports(
                entry_file,
                self.project_root,
            )
            directories.update(detected_dirs)
            files.update(detected_files)

            if detected_dirs or detected_files:
                logger.info(
                    f"Auto-detected imports: {len(detected_dirs)} directories, {len(detected_files)} files"
                )
        except Exception as e:
            self.warnings.append(f"Error auto-detecting imports: {e}")

        return directories, files

    def _validate_entrypoint_not_excluded(
        self,
        dirs: Set[str],
        files: Set[str],
        excludes: List[str],
    ) -> None:
        """
        Validate that entrypoint modules are not excluded.

        Raises:
            BuildConflictError: If entrypoint is excluded
        """
        entrypoint = self.spec.agent.entrypoint or self.spec.agent.handler
        conflicts: List[str] = []

        for d in dirs:
            if matches_pattern(d, excludes):
                conflicts.append(f"  - {d}/ (entrypoint directory)")

        for f in files:
            if matches_pattern(f, excludes):
                conflicts.append(f"  - {f} (entrypoint file)")

        if conflicts:
            raise BuildConflictError(
                f"Cannot exclude entrypoint module(s):\n"
                + "\n".join(conflicts)
                + f"\n\nRequired by entrypoint: {entrypoint}\n"
                f"Remove from 'build.exclude' to fix.",
                conflicts=[c.strip("- ") for c in conflicts],
            )

    def _validate_auto_detected_not_excluded(
        self,
        dirs: Set[str],
        files: Set[str],
        excludes: List[str],
    ) -> None:
        """
        Validate that auto-detected imports are not excluded.

        Raises:
            BuildConflictError: If auto-detected import is excluded
        """
        conflicts: List[str] = []

        for d in dirs:
            if matches_pattern(d, excludes):
                conflicts.append(f"  - {d}/ (auto-detected import)")

        for f in files:
            if matches_pattern(f, excludes):
                conflicts.append(f"  - {f} (auto-detected import)")

        if conflicts:
            raise BuildConflictError(
                f"Auto-detected imports are excluded from build:\n"
                + "\n".join(conflicts)
                + "\n\nOptions:\n"
                "  1. Remove from 'build.exclude'\n"
                "  2. Set 'build.auto_detect_imports: false' and use explicit includes",
                conflicts=[c.strip("- ") for c in conflicts],
            )

    def _warn_explicit_include_conflicts(
        self,
        dirs: Set[str],
        files: Set[str],
        excludes: List[str],
    ) -> None:
        """
        Add warnings for explicit includes that are also excluded.

        Exclude wins, but user should be warned.
        """
        for d in dirs:
            if matches_pattern(d, excludes):
                self.warnings.append(
                    f"'{d}' is in both include and exclude. "
                    f"Excluding it (exclude takes priority)."
                )

        for f in files:
            if matches_pattern(f, excludes):
                self.warnings.append(
                    f"'{f}' is in both include and exclude. "
                    f"Excluding it (exclude takes priority)."
                )

    def _validate_existence(
        self,
        dirs: Set[str],
        files: Set[str],
    ) -> None:
        """
        Validate that included items exist.

        Adds warnings for non-existent items.
        """
        for d in dirs:
            dir_path = self.project_root / d
            if not dir_path.is_dir():
                self.warnings.append(f"Directory '{d}' does not exist. Docker build may fail.")

        for f in files:
            file_path = self.project_root / f
            if not file_path.is_file():
                self.warnings.append(f"File '{f}' does not exist. Docker build may fail.")

