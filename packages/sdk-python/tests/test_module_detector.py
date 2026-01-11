"""Tests for module_detector.py - Module type detection."""

from pathlib import Path

import pytest

from dockrion_sdk.build.module_detector import (
    ModuleInfo,
    ModuleType,
    detect_module_type,
    resolve_entrypoint_modules,
)


class TestModuleType:
    """Tests for ModuleType enum."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        assert ModuleType.PACKAGE.value == "package"
        assert ModuleType.FILE.value == "file"
        assert ModuleType.NAMESPACE.value == "namespace"
        assert ModuleType.AMBIGUOUS.value == "ambiguous"
        assert ModuleType.NOT_FOUND.value == "not_found"


class TestDetectModuleType:
    """Tests for detect_module_type function."""

    def test_detect_package_with_init(self, tmp_path):
        """Test detection of package with __init__.py."""
        # Create package structure
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")

        info = detect_module_type("mypackage", tmp_path)

        assert info.type == ModuleType.PACKAGE
        assert info.name == "mypackage"
        assert info.path == pkg_dir
        assert info.warning is None

    def test_detect_single_file(self, tmp_path):
        """Test detection of single .py file."""
        # Create single file
        file_path = tmp_path / "mymodule.py"
        file_path.write_text("# My module")

        info = detect_module_type("mymodule", tmp_path)

        assert info.type == ModuleType.FILE
        assert info.name == "mymodule"
        assert info.path == file_path
        assert info.warning is None

    def test_detect_namespace_package(self, tmp_path):
        """Test detection of namespace package (no __init__.py)."""
        # Create directory without __init__.py
        ns_dir = tmp_path / "namespace_pkg"
        ns_dir.mkdir()

        info = detect_module_type("namespace_pkg", tmp_path)

        assert info.type == ModuleType.NAMESPACE
        assert info.name == "namespace_pkg"
        assert info.path == ns_dir
        assert info.warning is not None
        assert "namespace package" in info.warning

    def test_detect_ambiguous_both_exist(self, tmp_path):
        """Test detection when both file and directory exist."""
        # Create both file and directory
        file_path = tmp_path / "ambiguous.py"
        file_path.write_text("# File module")

        pkg_dir = tmp_path / "ambiguous"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")

        info = detect_module_type("ambiguous", tmp_path)

        assert info.type == ModuleType.AMBIGUOUS
        assert info.name == "ambiguous"
        # Package takes precedence
        assert info.path == pkg_dir
        assert info.warning is not None
        assert "Both" in info.warning

    def test_detect_not_found(self, tmp_path):
        """Test detection when module doesn't exist."""
        info = detect_module_type("nonexistent", tmp_path)

        assert info.type == ModuleType.NOT_FOUND
        assert info.name == "nonexistent"
        assert info.warning is not None
        assert "not found" in info.warning


class TestResolveEntrypointModules:
    """Tests for resolve_entrypoint_modules function."""

    def test_single_level_package(self, tmp_path):
        """Test resolving single-level package entrypoint."""
        # Create package
        pkg_dir = tmp_path / "app"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("def build_agent(): pass")

        dirs, files, warnings = resolve_entrypoint_modules("app:build_agent", tmp_path)

        assert "app" in dirs
        assert len(files) == 0
        assert len(warnings) == 0

    def test_single_level_file(self, tmp_path):
        """Test resolving single-level file entrypoint."""
        # Create single file
        (tmp_path / "agent.py").write_text("def run(): pass")

        dirs, files, warnings = resolve_entrypoint_modules("agent:run", tmp_path)

        assert len(dirs) == 0
        assert "agent.py" in files
        assert len(warnings) == 0

    def test_multi_level_package(self, tmp_path):
        """Test resolving multi-level package entrypoint."""
        # Create nested package
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        app_dir = src_dir / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("def handler(): pass")

        dirs, files, warnings = resolve_entrypoint_modules("src.app:handler", tmp_path)

        assert "src" in dirs
        assert len(files) == 0

    def test_invalid_entrypoint_format(self, tmp_path):
        """Test invalid entrypoint without colon."""
        dirs, files, warnings = resolve_entrypoint_modules("no_colon", tmp_path)

        assert len(dirs) == 0
        assert len(files) == 0
        assert len(warnings) == 1
        assert "Invalid entrypoint" in warnings[0]

    def test_entrypoint_not_found_assumes_directory(self, tmp_path):
        """Test that non-existent module assumes directory for backward compat."""
        dirs, files, warnings = resolve_entrypoint_modules("nonexistent:func", tmp_path)

        # Should assume directory for backward compatibility
        assert "nonexistent" in dirs
        assert len(files) == 0

    def test_file_with_dots_error(self, tmp_path):
        """Test error when dotted path refers to a file at top level."""
        # Create file at top level
        (tmp_path / "myfile.py").write_text("def func(): pass")

        dirs, files, warnings = resolve_entrypoint_modules("myfile.submodule:func", tmp_path)

        # Should warn about invalid configuration
        assert len(warnings) > 0
        assert any("is a file" in w for w in warnings)

    def test_ambiguous_module_warning(self, tmp_path):
        """Test warning when both file and package exist."""
        # Create both
        (tmp_path / "app.py").write_text("def func(): pass")
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")

        dirs, files, warnings = resolve_entrypoint_modules("app:func", tmp_path)

        # Package should win
        assert "app" in dirs
        assert len(files) == 0
        # Should have warning about ambiguity
        assert any("Both" in w for w in warnings)

