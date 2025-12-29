"""Tests for info commands (version, doctor)."""

from typer.testing import CliRunner

from dockrion_cli.main import app

runner = CliRunner()


def test_version():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
    assert "Python" in result.stdout


def test_doctor():
    """Test doctor command."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "diagnostic" in result.stdout.lower() or "check" in result.stdout.lower()
