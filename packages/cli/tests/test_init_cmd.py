"""Tests for init command."""
import pytest
from pathlib import Path
from typer.testing import CliRunner
from dockrion_cli.main import app

runner = CliRunner()


def test_init_creates_dockfile(tmp_path, monkeypatch):
    """Test init command creates a Dockfile."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "test-agent"])
    assert result.exit_code == 0
    assert Path("Dockfile.yaml").exists()
    assert "test-agent" in Path("Dockfile.yaml").read_text()


def test_init_with_custom_output(tmp_path, monkeypatch):
    """Test init with custom output path."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "test-agent", "--output", "custom.yaml"])
    assert result.exit_code == 0
    assert Path("custom.yaml").exists()


def test_init_existing_file_no_force(tmp_path, monkeypatch):
    """Test init with existing file without force."""
    monkeypatch.chdir(tmp_path)
    Path("Dockfile.yaml").write_text("existing")
    result = runner.invoke(app, ["init", "test-agent"], input="n\n")
    assert result.exit_code == 0
    assert Path("Dockfile.yaml").read_text() == "existing"


def test_init_with_force(tmp_path, monkeypatch):
    """Test init with force flag."""
    monkeypatch.chdir(tmp_path)
    Path("Dockfile.yaml").write_text("existing")
    result = runner.invoke(app, ["init", "test-agent", "--force"])
    assert result.exit_code == 0
    assert "test-agent" in Path("Dockfile.yaml").read_text()

