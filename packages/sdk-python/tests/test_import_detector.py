"""Tests for import_detector.py - AST-based import detection."""

from pathlib import Path

import pytest

from dockrion_sdk.build.import_detector import (
    detect_local_imports,
    find_entry_file,
)


class TestFindEntryFile:
    """Tests for find_entry_file function."""

    def test_find_single_file(self, tmp_path):
        """Test finding a single .py file."""
        file_path = tmp_path / "agent.py"
        file_path.write_text("def run(): pass")

        result = find_entry_file("agent", tmp_path)

        assert result == file_path

    def test_find_package_init(self, tmp_path):
        """Test finding package __init__.py."""
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        init_path = pkg_dir / "__init__.py"
        init_path.write_text("def handler(): pass")

        result = find_entry_file("mypackage", tmp_path)

        assert result == init_path

    def test_find_nested_module(self, tmp_path):
        """Test finding nested module file."""
        # Create src/app/main.py
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        app_dir = src_dir / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")

        main_file = app_dir / "main.py"
        main_file.write_text("def handler(): pass")

        result = find_entry_file("src.app.main", tmp_path)

        assert result == main_file

    def test_find_nested_package(self, tmp_path):
        """Test finding nested package __init__.py."""
        # Create src/app/__init__.py
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        app_dir = src_dir / "app"
        app_dir.mkdir()
        init_path = app_dir / "__init__.py"
        init_path.write_text("def handler(): pass")

        result = find_entry_file("src.app", tmp_path)

        assert result == init_path

    def test_not_found(self, tmp_path):
        """Test when module is not found."""
        result = find_entry_file("nonexistent", tmp_path)

        assert result is None


class TestDetectLocalImports:
    """Tests for detect_local_imports function."""

    def test_detect_simple_import(self, tmp_path):
        """Test detecting simple import statement."""
        # Create main.py that imports utils
        main_file = tmp_path / "main.py"
        main_file.write_text("import utils\n\ndef run(): pass")

        # Create utils package
        utils_dir = tmp_path / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("")

        dirs, files = detect_local_imports(main_file, tmp_path)

        assert "utils" in dirs

    def test_detect_from_import(self, tmp_path):
        """Test detecting from...import statement."""
        main_file = tmp_path / "main.py"
        main_file.write_text("from helpers import do_something\n")

        # Create helpers.py file
        (tmp_path / "helpers.py").write_text("def do_something(): pass")

        dirs, files = detect_local_imports(main_file, tmp_path)

        assert "helpers.py" in files

    def test_ignore_stdlib_imports(self, tmp_path):
        """Test that standard library imports are ignored."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
import os
import sys
from pathlib import Path
import json
""")

        dirs, files = detect_local_imports(main_file, tmp_path)

        assert len(dirs) == 0
        assert len(files) == 0

    def test_ignore_thirdparty_imports(self, tmp_path):
        """Test that third-party imports are ignored."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
import numpy
import pandas
from langchain import chains
""")

        dirs, files = detect_local_imports(main_file, tmp_path)

        assert len(dirs) == 0
        assert len(files) == 0

    def test_circular_import_handling(self, tmp_path):
        """Test that circular imports don't cause infinite recursion."""
        # Create two files that import each other
        a_file = tmp_path / "module_a.py"
        b_file = tmp_path / "module_b.py"

        a_file.write_text("import module_b")
        b_file.write_text("import module_a")

        # Should complete without error
        dirs, files = detect_local_imports(a_file, tmp_path)

        assert "module_b.py" in files

    def test_recursive_detection(self, tmp_path):
        """Test that imports are detected recursively."""
        # main.py imports utils, utils imports helpers
        main_file = tmp_path / "main.py"
        main_file.write_text("import utils")

        utils_dir = tmp_path / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("import helpers")

        (tmp_path / "helpers.py").write_text("def help(): pass")

        dirs, files = detect_local_imports(main_file, tmp_path)

        assert "utils" in dirs
        assert "helpers.py" in files

    def test_syntax_error_handling(self, tmp_path):
        """Test that syntax errors are handled gracefully."""
        main_file = tmp_path / "main.py"
        main_file.write_text("this is not valid python !!!")

        # Should not raise, just return empty
        dirs, files = detect_local_imports(main_file, tmp_path)

        assert len(dirs) == 0
        assert len(files) == 0

    def test_file_not_found(self, tmp_path):
        """Test handling of non-existent file."""
        nonexistent = tmp_path / "nonexistent.py"

        dirs, files = detect_local_imports(nonexistent, tmp_path)

        assert len(dirs) == 0
        assert len(files) == 0

    def test_empty_file(self, tmp_path):
        """Test handling of empty file."""
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        dirs, files = detect_local_imports(empty_file, tmp_path)

        assert len(dirs) == 0
        assert len(files) == 0

    def test_multiple_imports(self, tmp_path):
        """Test detecting multiple imports."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
import utils
import helpers
from models import User
""")

        # Create local modules
        (tmp_path / "utils").mkdir()
        (tmp_path / "utils" / "__init__.py").write_text("")

        (tmp_path / "helpers.py").write_text("")

        (tmp_path / "models").mkdir()
        (tmp_path / "models" / "__init__.py").write_text("class User: pass")

        dirs, files = detect_local_imports(main_file, tmp_path)

        assert "utils" in dirs
        assert "models" in dirs
        assert "helpers.py" in files
