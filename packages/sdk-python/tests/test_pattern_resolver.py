"""Tests for pattern_resolver.py - Glob pattern resolution and matching."""

from pathlib import Path

import pytest

from dockrion_sdk.build.pattern_resolver import (
    filter_by_excludes,
    matches_pattern,
    resolve_glob_patterns,
)


class TestResolveGlobPatterns:
    """Tests for resolve_glob_patterns function."""

    def test_simple_file_pattern(self, tmp_path):
        """Test resolving simple file patterns."""
        # Create test files
        (tmp_path / "config.json").write_text("{}")
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "script.py").write_text("")

        dirs, files = resolve_glob_patterns(["*.json"], tmp_path)

        assert len(dirs) == 0
        assert "config.json" in files
        assert "data.json" in files
        assert "script.py" not in files

    def test_recursive_pattern(self, tmp_path):
        """Test resolving recursive patterns with **."""
        # Create nested structure
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "input.json").write_text("{}")

        nested_dir = data_dir / "nested"
        nested_dir.mkdir()
        (nested_dir / "output.json").write_text("{}")

        dirs, files = resolve_glob_patterns(["**/*.json"], tmp_path)

        # Should find files in nested directories
        assert any("input.json" in f for f in files)
        assert any("output.json" in f for f in files)

    def test_directory_pattern(self, tmp_path):
        """Test resolving directory patterns."""
        # Create directories
        (tmp_path / "utils").mkdir()
        (tmp_path / "helpers").mkdir()
        (tmp_path / "main.py").write_text("")

        dirs, files = resolve_glob_patterns(["utils", "helpers"], tmp_path)

        assert "utils" in dirs
        assert "helpers" in dirs
        assert len(files) == 0

    def test_empty_patterns(self, tmp_path):
        """Test with empty pattern list."""
        dirs, files = resolve_glob_patterns([], tmp_path)

        assert len(dirs) == 0
        assert len(files) == 0

    def test_no_matches(self, tmp_path):
        """Test pattern with no matches."""
        (tmp_path / "file.txt").write_text("")

        dirs, files = resolve_glob_patterns(["*.nonexistent"], tmp_path)

        assert len(dirs) == 0
        assert len(files) == 0

    def test_hidden_files_skipped(self, tmp_path):
        """Test that hidden files are skipped."""
        (tmp_path / ".hidden.json").write_text("{}")
        (tmp_path / "visible.json").write_text("{}")

        dirs, files = resolve_glob_patterns(["*.json"], tmp_path)

        assert ".hidden.json" not in files
        assert "visible.json" in files


class TestMatchesPattern:
    """Tests for matches_pattern function."""

    def test_exact_match(self):
        """Test exact path matching."""
        assert matches_pattern("tests", ["tests"]) is True
        assert matches_pattern("tests", ["src"]) is False

    def test_exact_match_with_trailing_slash(self):
        """Test exact match with trailing slash."""
        assert matches_pattern("tests", ["tests/"]) is True
        assert matches_pattern("tests/unit", ["tests/"]) is True

    def test_glob_pattern(self):
        """Test glob pattern matching."""
        assert matches_pattern("module.pyc", ["*.pyc"]) is True
        assert matches_pattern("module.py", ["*.pyc"]) is False

    def test_recursive_pattern(self):
        """Test recursive ** pattern matching."""
        assert matches_pattern("app/__pycache__", ["**/__pycache__"]) is True
        assert matches_pattern("deep/nested/__pycache__", ["**/__pycache__"]) is True
        assert matches_pattern("__pycache__", ["**/__pycache__"]) is True

    def test_no_match(self):
        """Test when no patterns match."""
        assert matches_pattern("src/main.py", ["tests/", "*.txt"]) is False

    def test_multiple_patterns(self):
        """Test matching against multiple patterns."""
        patterns = ["tests/", "*.pyc", "**/__pycache__"]

        assert matches_pattern("tests", patterns) is True
        assert matches_pattern("module.pyc", patterns) is True
        assert matches_pattern("src/__pycache__", patterns) is True
        assert matches_pattern("src/main.py", patterns) is False

    def test_path_normalization(self):
        """Test that path separators are normalized."""
        # Windows-style path
        assert matches_pattern("src\\tests", ["src/tests"]) is True


class TestFilterByExcludes:
    """Tests for filter_by_excludes function."""

    def test_basic_filtering(self):
        """Test basic exclude filtering."""
        items = {"app", "tests", "utils", "docs"}
        result = filter_by_excludes(items, ["tests/", "docs/"])

        assert "app" in result
        assert "utils" in result
        assert "tests" not in result
        assert "docs" not in result

    def test_no_excludes(self):
        """Test with empty exclude list."""
        items = {"app", "utils"}
        result = filter_by_excludes(items, [])

        assert set(result) == items

    def test_all_excluded(self):
        """Test when all items are excluded."""
        items = {"tests", "__pycache__"}
        result = filter_by_excludes(items, ["tests/", "**/__pycache__"])

        assert len(result) == 0

    def test_result_sorted(self):
        """Test that result is sorted."""
        items = {"zebra", "apple", "mango"}
        result = filter_by_excludes(items, [])

        assert result == ["apple", "mango", "zebra"]

    def test_pattern_matching(self):
        """Test exclude with glob patterns."""
        items = {"module.pyc", "module.py", "test.pyc"}
        result = filter_by_excludes(items, ["*.pyc"])

        assert "module.py" in result
        assert "module.pyc" not in result
        assert "test.pyc" not in result

