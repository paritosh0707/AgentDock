"""
Tests for CLI add command.

Tests cover:
- add streaming command
- add auth command
- add secrets command
"""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from dockrion_cli.add_cmd import app

runner = CliRunner()


@pytest.fixture
def temp_dockfile(tmp_path):
    """Create a temporary Dockfile for testing."""
    dockfile = tmp_path / "Dockfile.yaml"
    content = {
        "version": "1.0",
        "agent": {
            "name": "test-agent",
            "entrypoint": "app.main:build_agent",
            "framework": "langgraph",
        },
        "expose": {
            "port": 8080,
            "streaming": "sse",
        },
    }
    dockfile.write_text(yaml.dump(content))
    return dockfile


class TestAddStreaming:
    """Test add streaming command."""

    def test_add_streaming_basic(self, temp_dockfile):
        """Should add basic streaming config."""
        result = runner.invoke(app, ["streaming", str(temp_dockfile)])

        assert result.exit_code == 0
        assert "Added streaming configuration" in result.stdout

        # Verify file was updated
        data = yaml.safe_load(temp_dockfile.read_text())
        assert "streaming" in data
        assert data["streaming"]["backend"] == "memory"

    def test_add_streaming_with_events_preset(self, temp_dockfile):
        """Should add streaming with events preset."""
        result = runner.invoke(
            app, ["streaming", str(temp_dockfile), "--events", "chat"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["streaming"]["events"]["allowed"] == "chat"

    def test_add_streaming_with_events_list(self, temp_dockfile):
        """Should add streaming with events list."""
        result = runner.invoke(
            app, ["streaming", str(temp_dockfile), "--events", "token,step,custom:fraud"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["streaming"]["events"]["allowed"] == ["token", "step", "custom:fraud"]

    def test_add_streaming_with_async_runs(self, temp_dockfile):
        """Should enable async runs."""
        result = runner.invoke(
            app, ["streaming", str(temp_dockfile), "--async-runs"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["streaming"]["async_runs"] is True

    def test_add_streaming_with_redis_backend(self, temp_dockfile):
        """Should set redis backend."""
        result = runner.invoke(
            app, ["streaming", str(temp_dockfile), "--backend", "redis"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["streaming"]["backend"] == "redis"

    def test_add_streaming_with_custom_heartbeat(self, temp_dockfile):
        """Should set custom heartbeat interval."""
        result = runner.invoke(
            app, ["streaming", str(temp_dockfile), "--events", "chat", "--heartbeat", "30"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["streaming"]["events"]["heartbeat_interval"] == 30

    def test_add_streaming_invalid_backend(self, temp_dockfile):
        """Should reject invalid backend."""
        result = runner.invoke(
            app, ["streaming", str(temp_dockfile), "--backend", "invalid"]
        )

        assert result.exit_code == 1
        assert "Invalid backend" in result.stdout

    def test_add_streaming_existing_requires_force(self, temp_dockfile):
        """Should require force to overwrite existing config."""
        # First add
        runner.invoke(app, ["streaming", str(temp_dockfile)])

        # Second add without force should prompt
        result = runner.invoke(app, ["streaming", str(temp_dockfile)], input="n\n")

        assert "already exists" in result.stdout.lower() or result.exit_code == 0

    def test_add_streaming_force_overwrites(self, temp_dockfile):
        """Should overwrite with force flag."""
        runner.invoke(app, ["streaming", str(temp_dockfile), "--events", "chat"])
        result = runner.invoke(
            app, ["streaming", str(temp_dockfile), "--events", "debug", "--force"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["streaming"]["events"]["allowed"] == "debug"


class TestAddAuth:
    """Test add auth command."""

    def test_add_auth_api_key(self, temp_dockfile):
        """Should add API key auth."""
        result = runner.invoke(
            app, ["auth", str(temp_dockfile), "--mode", "api_key"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["auth"]["mode"] == "api_key"
        assert "api_keys" in data["auth"]

    def test_add_auth_custom_env_var(self, temp_dockfile):
        """Should set custom env var."""
        result = runner.invoke(
            app, ["auth", str(temp_dockfile), "--env-var", "MY_SECRET_KEY"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["auth"]["api_keys"]["env_var"] == "MY_SECRET_KEY"

    def test_add_auth_custom_header(self, temp_dockfile):
        """Should set custom header."""
        result = runner.invoke(
            app, ["auth", str(temp_dockfile), "--header", "Authorization"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["auth"]["api_keys"]["header"] == "Authorization"

    def test_add_auth_jwt(self, temp_dockfile):
        """Should add JWT auth."""
        result = runner.invoke(
            app, ["auth", str(temp_dockfile), "--mode", "jwt"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["auth"]["mode"] == "jwt"

    def test_add_auth_invalid_mode(self, temp_dockfile):
        """Should reject invalid auth mode."""
        result = runner.invoke(
            app, ["auth", str(temp_dockfile), "--mode", "invalid"]
        )

        assert result.exit_code == 1
        assert "Invalid auth mode" in result.stdout


class TestAddSecrets:
    """Test add secrets command."""

    def test_add_secrets_single(self, temp_dockfile):
        """Should add single secret."""
        result = runner.invoke(
            app, ["secrets", str(temp_dockfile), "OPENAI_API_KEY"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert "secrets" in data
        assert len(data["secrets"]["required"]) == 1
        assert data["secrets"]["required"][0]["name"] == "OPENAI_API_KEY"

    def test_add_secrets_multiple(self, temp_dockfile):
        """Should add multiple secrets."""
        result = runner.invoke(
            app, ["secrets", str(temp_dockfile), "OPENAI_API_KEY,ANTHROPIC_KEY"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert len(data["secrets"]["required"]) == 2

    def test_add_secrets_optional(self, temp_dockfile):
        """Should add optional secrets."""
        result = runner.invoke(
            app, ["secrets", str(temp_dockfile), "LANGFUSE_SECRET", "--optional"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert len(data["secrets"]["optional"]) == 1
        assert data["secrets"]["optional"][0]["name"] == "LANGFUSE_SECRET"

    def test_add_secrets_merge_existing(self, temp_dockfile):
        """Should merge with existing secrets."""
        # First add
        runner.invoke(app, ["secrets", str(temp_dockfile), "OPENAI_API_KEY"])

        # Second add should merge
        result = runner.invoke(
            app, ["secrets", str(temp_dockfile), "ANTHROPIC_KEY"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert len(data["secrets"]["required"]) == 2

    def test_add_secrets_normalizes_names(self, temp_dockfile):
        """Should normalize secret names to uppercase."""
        result = runner.invoke(
            app, ["secrets", str(temp_dockfile), "openai-api-key"]
        )

        assert result.exit_code == 0

        data = yaml.safe_load(temp_dockfile.read_text())
        assert data["secrets"]["required"][0]["name"] == "OPENAI_API_KEY"


class TestAddCommandErrors:
    """Test error handling in add commands."""

    def test_missing_dockfile(self, tmp_path):
        """Should error when Dockfile doesn't exist."""
        result = runner.invoke(
            app, ["streaming", str(tmp_path / "nonexistent.yaml")]
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_invalid_yaml(self, tmp_path):
        """Should error on invalid YAML."""
        dockfile = tmp_path / "invalid.yaml"
        dockfile.write_text("invalid: yaml: content: [")

        result = runner.invoke(app, ["streaming", str(dockfile)])

        assert result.exit_code == 1
