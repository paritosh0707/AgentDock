"""Tests for resolver.py - BuildResolver class."""

from pathlib import Path
from typing import Any

import pytest
from dockrion_common import BuildConflictError
from dockrion_schema import DockSpec

from dockrion_sdk.build.resolver import BuildResolution, BuildResolver


def create_spec(
    entrypoint: str | None = "app:handler",
    handler: str | None = None,
    include_dirs: list[str] | None = None,
    include_files: list[str] | None = None,
    include_patterns: list[str] | None = None,
    exclude: list[str] | None = None,
    auto_detect_imports: bool = False,
) -> DockSpec:
    """Create a DockSpec for testing."""
    agent_dict: dict[str, Any] = {
        "name": "test-agent",
        "framework": "langgraph",
    }

    if entrypoint:
        agent_dict["entrypoint"] = entrypoint

    spec_dict: dict[str, Any] = {
        "version": "1.0",
        "agent": agent_dict,
        "io_schema": {
            "input": {"type": "object"},
            "output": {"type": "object"},
        },
        "expose": {"port": 8080},
    }

    if handler:
        spec_dict["agent"]["handler"] = handler
        if "entrypoint" in spec_dict["agent"]:
            del spec_dict["agent"]["entrypoint"]

    # Add build config if any build options are provided
    if any([include_dirs, include_files, include_patterns, exclude, auto_detect_imports]):
        build_config: dict[str, Any] = {"auto_detect_imports": auto_detect_imports}

        if include_dirs or include_files or include_patterns:
            build_config["include"] = {}
            if include_dirs:
                build_config["include"]["directories"] = include_dirs
            if include_files:
                build_config["include"]["files"] = include_files
            if include_patterns:
                build_config["include"]["patterns"] = include_patterns

        if exclude:
            build_config["exclude"] = exclude

        spec_dict["build"] = build_config

    return DockSpec.model_validate(spec_dict)


class TestBuildResolution:
    """Tests for BuildResolution dataclass."""

    def test_default_values(self):
        """Test default values for BuildResolution."""
        resolution = BuildResolution()

        assert resolution.directories == []
        assert resolution.files == []
        assert resolution.warnings == []

    def test_with_values(self):
        """Test BuildResolution with values."""
        resolution = BuildResolution(
            directories=["app", "utils"],
            files=["config.py"],
            warnings=["Warning 1"],
        )

        assert resolution.directories == ["app", "utils"]
        assert resolution.files == ["config.py"]
        assert resolution.warnings == ["Warning 1"]


class TestBuildResolverBasic:
    """Tests for basic BuildResolver functionality."""

    def test_resolve_package_entrypoint(self, tmp_path):
        """Test resolving package entrypoint."""
        # Create package
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("def handler(): pass")

        spec = create_spec(entrypoint="app:handler")
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert "app" in resolution.directories
        assert len(resolution.files) == 0

    def test_resolve_file_entrypoint(self, tmp_path):
        """Test resolving single-file entrypoint."""
        # Create file
        (tmp_path / "agent.py").write_text("def run(): pass")

        spec = create_spec(entrypoint="agent:run")
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert len(resolution.directories) == 0
        assert "agent.py" in resolution.files

    def test_resolve_handler_mode(self, tmp_path):
        """Test resolving with handler instead of entrypoint."""
        # Create package
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("def create(): pass")

        spec = create_spec(entrypoint=None, handler="app:create")
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert "app" in resolution.directories


class TestBuildResolverExplicitIncludes:
    """Tests for explicit include configuration."""

    def test_include_directories(self, tmp_path):
        """Test including additional directories."""
        # Create entrypoint
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")

        # Create additional directories
        (tmp_path / "utils").mkdir()
        (tmp_path / "utils" / "__init__.py").write_text("")
        (tmp_path / "models").mkdir()
        (tmp_path / "models" / "__init__.py").write_text("")

        spec = create_spec(
            entrypoint="app:handler",
            include_dirs=["utils", "models"],
        )
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert "app" in resolution.directories
        assert "utils" in resolution.directories
        assert "models" in resolution.directories

    def test_include_files(self, tmp_path):
        """Test including additional files."""
        # Create entrypoint
        (tmp_path / "agent.py").write_text("def run(): pass")

        # Create additional files
        (tmp_path / "config.yaml").write_text("key: value")
        (tmp_path / "constants.py").write_text("FOO = 1")

        spec = create_spec(
            entrypoint="agent:run",
            include_files=["config.yaml", "constants.py"],
        )
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert "agent.py" in resolution.files
        assert "config.yaml" in resolution.files
        assert "constants.py" in resolution.files


class TestBuildResolverExcludes:
    """Tests for exclude patterns."""

    def test_exclude_directory(self, tmp_path):
        """Test excluding a directory."""
        # Create entrypoint
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")

        # Create directories - tests should be excluded
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "__init__.py").write_text("")

        spec = create_spec(
            entrypoint="app:handler",
            include_dirs=["tests"],  # Include it
            exclude=["tests/"],  # But exclude it
        )
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert "app" in resolution.directories
        assert "tests" not in resolution.directories
        # Should have warning about conflict
        assert any("tests" in w for w in resolution.warnings)

    def test_exclude_pattern(self, tmp_path):
        """Test excluding with glob pattern."""
        # Create entrypoint file
        (tmp_path / "agent.py").write_text("def run(): pass")

        # Create files to include/exclude
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "data.pyc").write_text("")

        spec = create_spec(
            entrypoint="agent:run",
            include_files=["data.json", "data.pyc"],
            exclude=["*.pyc"],
        )
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert "data.json" in resolution.files
        assert "data.pyc" not in resolution.files


class TestBuildResolverConflicts:
    """Tests for conflict detection."""

    def test_entrypoint_excluded_raises_error(self, tmp_path):
        """Test that excluding entrypoint raises error."""
        # Create entrypoint
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")

        spec = create_spec(
            entrypoint="app:handler",
            exclude=["app/"],
        )
        resolver = BuildResolver(spec, tmp_path)

        with pytest.raises(BuildConflictError) as exc_info:
            resolver.resolve()

        assert "entrypoint" in str(exc_info.value).lower()

    def test_auto_detected_excluded_raises_error(self, tmp_path):
        """Test that excluding auto-detected imports raises error."""
        # Create entrypoint that imports utils
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("import utils\ndef handler(): pass")

        # Create utils that will be auto-detected
        utils_dir = tmp_path / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("")

        spec = create_spec(
            entrypoint="app:handler",
            auto_detect_imports=True,
            exclude=["utils/"],
        )
        resolver = BuildResolver(spec, tmp_path)

        with pytest.raises(BuildConflictError) as exc_info:
            resolver.resolve()

        assert "utils" in str(exc_info.value).lower()


class TestBuildResolverAutoDetect:
    """Tests for auto-detect imports feature."""

    def test_auto_detect_local_imports(self, tmp_path):
        """Test auto-detecting local imports."""
        # Create entrypoint that imports utils
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("""
import utils
from helpers import do_something

def handler():
    pass
""")

        # Create local modules
        utils_dir = tmp_path / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("")

        (tmp_path / "helpers.py").write_text("def do_something(): pass")

        spec = create_spec(
            entrypoint="app:handler",
            auto_detect_imports=True,
        )
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert "app" in resolution.directories
        assert "utils" in resolution.directories
        assert "helpers.py" in resolution.files

    def test_auto_detect_disabled_by_default(self, tmp_path):
        """Test that auto-detect is disabled by default."""
        # Create entrypoint that imports utils
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("import utils\ndef handler(): pass")

        # Create utils
        utils_dir = tmp_path / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("")

        spec = create_spec(entrypoint="app:handler")
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert "app" in resolution.directories
        # utils should NOT be included without auto_detect
        assert "utils" not in resolution.directories


class TestBuildResolverWarnings:
    """Tests for warning generation."""

    def test_nonexistent_include_warning(self, tmp_path):
        """Test warning for non-existent includes."""
        # Create entrypoint
        (tmp_path / "agent.py").write_text("def run(): pass")

        spec = create_spec(
            entrypoint="agent:run",
            include_dirs=["nonexistent"],
        )
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        assert any("nonexistent" in w and "does not exist" in w for w in resolution.warnings)

    def test_include_exclude_conflict_warning(self, tmp_path):
        """Test warning when same item is in include and exclude."""
        # Create entrypoint
        (tmp_path / "agent.py").write_text("def run(): pass")

        # Create utils
        (tmp_path / "utils").mkdir()
        (tmp_path / "utils" / "__init__.py").write_text("")

        spec = create_spec(
            entrypoint="agent:run",
            include_dirs=["utils"],
            exclude=["utils/"],
        )
        resolver = BuildResolver(spec, tmp_path)
        resolution = resolver.resolve()

        # Should have warning
        assert any("both include and exclude" in w for w in resolution.warnings)
        # Exclude should win
        assert "utils" not in resolution.directories

