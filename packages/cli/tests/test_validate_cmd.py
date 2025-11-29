"""Tests for validate command."""
import pytest
from typer.testing import CliRunner
from dockrion_cli.main import app

runner = CliRunner()


def test_validate_valid_dockfile(sample_dockfile):
    """Test validating a valid Dockfile."""
    result = runner.invoke(app, ["validate", sample_dockfile])
    assert result.exit_code == 0
    assert "✅" in result.stdout or "valid" in result.stdout.lower()


def test_validate_file_not_found():
    """Test validating a non-existent file."""
    result = runner.invoke(app, ["validate", "nonexistent.yaml"])
    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def test_validate_with_verbose(sample_dockfile):
    """Test validate with verbose flag."""
    result = runner.invoke(app, ["validate", sample_dockfile, "--verbose"])
    assert result.exit_code == 0


def test_validate_with_quiet(sample_dockfile):
    """Test validate with quiet flag."""
    result = runner.invoke(app, ["validate", sample_dockfile, "--quiet"])
    assert result.exit_code == 0

