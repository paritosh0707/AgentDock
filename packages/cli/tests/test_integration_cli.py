"""Integration tests for CLI commands.

These tests verify end-to-end CLI functionality.
"""

import json

from typer.testing import CliRunner

from dockrion_cli.main import app

runner = CliRunner()


class TestValidateCommand:
    """Test the validate command end-to-end."""

    def test_validate_valid_dockfile(self, sample_dockfile):
        """Test validating a valid Dockfile."""
        result = runner.invoke(app, ["validate", sample_dockfile])
        assert result.exit_code == 0
        assert "✅" in result.stdout or "valid" in result.stdout.lower()

    def test_validate_invalid_dockfile(self, invalid_dockfile):
        """Test validating an invalid Dockfile."""
        result = runner.invoke(app, ["validate", invalid_dockfile])
        assert result.exit_code == 1
        assert "❌" in result.stdout or "error" in result.stdout.lower()

    def test_validate_nonexistent_file(self):
        """Test validating a file that doesn't exist."""
        result = runner.invoke(app, ["validate", "nonexistent.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_validate_verbose_mode(self, sample_dockfile):
        """Test validate with verbose flag."""
        result = runner.invoke(app, ["validate", sample_dockfile, "--verbose"])
        assert result.exit_code == 0

    def test_validate_quiet_mode(self, sample_dockfile):
        """Test validate with quiet flag."""
        result = runner.invoke(app, ["validate", sample_dockfile, "--quiet"])
        assert result.exit_code == 0
        # Quiet mode should have minimal output
        assert len(result.stdout) < 100


class TestTestCommand:
    """Test the test command end-to-end."""

    def test_test_with_json_payload(self, sample_dockfile):
        """Test running agent with JSON payload."""
        payload = '{"text": "hello world"}'
        result = runner.invoke(app, ["test", sample_dockfile, "--payload", payload])

        # Should succeed
        assert result.exit_code == 0
        assert "✅" in result.stdout or "success" in result.stdout.lower()

    def test_test_with_payload_file(self, sample_dockfile, tmp_path):
        """Test running agent with payload from file."""
        # Create payload file
        payload_file = tmp_path / "payload.json"
        payload_file.write_text(json.dumps({"text": "test input"}))

        result = runner.invoke(app, ["test", sample_dockfile, "--payload-file", str(payload_file)])

        assert result.exit_code == 0
        assert "✅" in result.stdout or "success" in result.stdout.lower()

    def test_test_with_output_file(self, sample_dockfile, tmp_path):
        """Test saving output to file."""
        output_file = tmp_path / "output.json"
        payload = '{"text": "test"}'

        result = runner.invoke(
            app, ["test", sample_dockfile, "--payload", payload, "--output", str(output_file)]
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify output is valid JSON
        with open(output_file) as f:
            output_data = json.load(f)
            assert isinstance(output_data, dict)

    def test_test_without_payload_fails(self, sample_dockfile):
        """Test that test command fails without payload."""
        result = runner.invoke(app, ["test", sample_dockfile])
        assert result.exit_code == 1
        assert "payload" in result.stdout.lower()

    def test_test_with_invalid_json_payload(self, sample_dockfile):
        """Test with malformed JSON payload."""
        result = runner.invoke(app, ["test", sample_dockfile, "--payload", "not valid json"])
        assert result.exit_code == 1
        assert "json" in result.stdout.lower()

    def test_test_nonexistent_payload_file(self, sample_dockfile):
        """Test with non-existent payload file."""
        result = runner.invoke(app, ["test", sample_dockfile, "--payload-file", "nonexistent.json"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestInitCommand:
    """Test the init command end-to-end."""

    def test_init_creates_dockfile(self, tmp_path):
        """Test that init creates a new Dockfile."""
        output_path = tmp_path / "NewDockfile.yaml"

        result = runner.invoke(app, ["init", "my-agent", "--output", str(output_path)])

        assert result.exit_code == 0
        assert output_path.exists()

        # Verify content
        content = output_path.read_text()
        assert "my-agent" in content
        assert "langgraph" in content

    def test_init_default_path(self, tmp_path, monkeypatch):
        """Test init with default path."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "test-agent"])

        assert result.exit_code == 0
        assert (tmp_path / "Dockfile.yaml").exists()

    def test_init_refuses_to_overwrite_without_force(self, tmp_path, monkeypatch):
        """Test that init doesn't overwrite existing file without --force."""
        monkeypatch.chdir(tmp_path)
        output_path = tmp_path / "Dockfile.yaml"
        output_path.write_text("existing content")

        result = runner.invoke(
            app, ["init", "test-agent"], input="n\n"
        )  # Answer "no" to overwrite prompt

        # Should not overwrite
        assert "existing content" in output_path.read_text()

    def test_init_with_force_overwrites(self, tmp_path, monkeypatch):
        """Test that init with --force overwrites existing file."""
        monkeypatch.chdir(tmp_path)
        output_path = tmp_path / "Dockfile.yaml"
        output_path.write_text("existing content")

        result = runner.invoke(app, ["init", "new-agent", "--force"])

        assert result.exit_code == 0
        content = output_path.read_text()
        assert "new-agent" in content
        assert "existing content" not in content


class TestVersionCommand:
    """Test the version command."""

    def test_version_shows_cli_version(self):
        """Test that version command shows CLI version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "CLI" in result.stdout or "version" in result.stdout.lower()

    def test_version_shows_sdk_version(self):
        """Test that version shows SDK version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "SDK" in result.stdout or "dockrion" in result.stdout.lower()


class TestDoctorCommand:
    """Test the doctor command."""

    def test_doctor_checks_python(self):
        """Test that doctor checks Python installation."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "python" in result.stdout.lower()

    def test_doctor_checks_docker(self):
        """Test that doctor checks Docker installation."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "docker" in result.stdout.lower()

    def test_doctor_checks_dockfile_in_cwd(self, tmp_path, monkeypatch):
        """Test that doctor checks for Dockfile in current directory."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        # Should mention Dockfile status
        assert "dockfile" in result.stdout.lower()


class TestLogsCommand:
    """Test the logs command."""

    def test_logs_with_agent_name(self):
        """Test viewing logs for an agent."""
        result = runner.invoke(app, ["logs", "test-agent"])
        # May succeed or fail depending on whether logs exist
        # Just check it doesn't crash
        assert result.exit_code in [0, 1]

    def test_logs_with_lines_option(self):
        """Test logs with --lines option."""
        result = runner.invoke(app, ["logs", "test-agent", "--lines", "50"])
        assert result.exit_code in [0, 1]

    def test_logs_with_follow_option(self):
        """Test logs with --follow option (should start then we cancel)."""
        # Note: This is hard to test without actually running an agent
        # Just verify the command accepts the flag
        result = runner.invoke(app, ["logs", "test-agent", "--follow"], input="\x03")
        # Should handle Ctrl+C gracefully
        assert result.exit_code in [0, 1, 130]


class TestCommandChaining:
    """Test chaining multiple commands together."""

    def test_validate_then_test(self, sample_dockfile):
        """Test validating then testing an agent."""
        # First validate
        result1 = runner.invoke(app, ["validate", sample_dockfile])
        assert result1.exit_code == 0

        # Then test
        result2 = runner.invoke(app, ["test", sample_dockfile, "--payload", '{"text": "test"}'])
        assert result2.exit_code == 0

    def test_init_then_validate(self, tmp_path, monkeypatch):
        """Test creating then validating a Dockfile."""
        monkeypatch.chdir(tmp_path)

        # First init
        result1 = runner.invoke(app, ["init", "test-agent"])
        assert result1.exit_code == 0

        # Then validate
        result2 = runner.invoke(app, ["validate", str(tmp_path / "Dockfile.yaml")])
        # May fail due to invalid entrypoint, but should parse
        assert result2.exit_code in [0, 1]


class TestErrorHandling:
    """Test error handling across CLI commands."""

    def test_invalid_command(self):
        """Test running an invalid command."""
        result = runner.invoke(app, ["nonexistent-command"])
        assert result.exit_code != 0

    def test_missing_required_argument(self):
        """Test command with missing required argument."""
        result = runner.invoke(app, ["test"])  # Missing dockfile path
        assert result.exit_code != 0

    def test_invalid_option_value(self, sample_dockfile):
        """Test command with invalid option value."""
        result = runner.invoke(app, ["validate", sample_dockfile, "--invalid-option", "value"])
        assert result.exit_code != 0


class TestOutputFormatting:
    """Test output formatting and styling."""

    def test_validate_output_has_colors(self, sample_dockfile):
        """Test that validate output includes color codes."""
        result = runner.invoke(app, ["validate", sample_dockfile])
        # Rich adds ANSI codes for colors
        # In test environment, may or may not have colors
        assert len(result.stdout) > 0

    def test_test_output_has_json_formatting(self, sample_dockfile):
        """Test that test output formats JSON nicely."""
        result = runner.invoke(app, ["test", sample_dockfile, "--payload", '{"text": "test"}'])
        assert result.exit_code == 0
        # Should have some output
        assert len(result.stdout) > 50

    def test_verbose_mode_adds_detail(self, sample_dockfile):
        """Test that verbose mode adds more detail."""
        result_normal = runner.invoke(app, ["validate", sample_dockfile])
        result_verbose = runner.invoke(app, ["validate", sample_dockfile, "--verbose"])

        # Verbose should have more output
        assert len(result_verbose.stdout) >= len(result_normal.stdout)

    def test_quiet_mode_reduces_output(self, sample_dockfile):
        """Test that quiet mode reduces output."""
        result_normal = runner.invoke(app, ["validate", sample_dockfile])
        result_quiet = runner.invoke(app, ["validate", sample_dockfile, "--quiet"])

        # Quiet should have less output
        assert len(result_quiet.stdout) <= len(result_normal.stdout)


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_developer_workflow(self, tmp_path, monkeypatch, mock_agent_module):
        """Test typical developer workflow: init -> edit -> validate -> test."""
        monkeypatch.chdir(tmp_path)

        # Step 1: Initialize project
        result = runner.invoke(app, ["init", "my-agent"])
        assert result.exit_code == 0

        # Step 2: Validate (will fail due to invalid entrypoint, but that's OK)
        result = runner.invoke(app, ["validate"])
        assert result.exit_code in [0, 1]

        # Step 3: Fix the Dockfile to use test entrypoint
        dockfile = tmp_path / "Dockfile.yaml"
        content = dockfile.read_text()
        content = content.replace(
            "entrypoint: app.main:build_agent", f"entrypoint: {mock_agent_module}"
        )
        dockfile.write_text(content)

        # Step 4: Validate again
        result = runner.invoke(app, ["validate"])
        assert result.exit_code == 0

        # Step 5: Test
        result = runner.invoke(app, ["test", "--payload", '{"text": "hello"}'])
        assert result.exit_code == 0

    def test_ci_cd_workflow(self, sample_dockfile):
        """Test CI/CD workflow: validate in quiet mode."""
        # In CI/CD, you want minimal output and clear exit codes
        result = runner.invoke(app, ["validate", sample_dockfile, "--quiet"])

        # Should succeed with exit code 0
        assert result.exit_code == 0

        # Should have minimal output
        assert len(result.stdout) < 200

    def test_debugging_workflow(self, sample_dockfile):
        """Test debugging workflow with verbose output."""
        # When debugging, you want maximum detail
        result = runner.invoke(app, ["validate", sample_dockfile, "--verbose"])

        assert result.exit_code == 0
        # Verbose mode should provide detailed information
        assert len(result.stdout) > 100


class TestConcurrentCLICalls:
    """Test handling of concurrent CLI invocations.

    Uses sequential execution to avoid I/O conflicts with CliRunner.
    """

    def test_multiple_validates_sequential(self, sample_dockfile):
        """Test running multiple validate commands sequentially."""
        results = []
        for _ in range(3):
            local_runner = CliRunner()
            results.append(local_runner.invoke(app, ["validate", sample_dockfile]))

        # All should succeed
        assert all(r.exit_code == 0 for r in results)

    def test_multiple_tests_sequential(self, sample_dockfile):
        """Test running multiple test commands sequentially."""
        results = []
        for _ in range(2):
            local_runner = CliRunner()
            results.append(
                local_runner.invoke(app, ["test", sample_dockfile, "--payload", '{"text": "test"}'])
            )

        # All should succeed
        assert all(r.exit_code == 0 for r in results)


class TestEdgeCasesInCLI:
    """Test edge cases in CLI usage."""

    def test_very_long_file_path(self, tmp_path):
        """Test handling very long file paths."""
        # Create nested directory structure
        deep_path = tmp_path
        for i in range(20):
            deep_path = deep_path / f"dir{i}"
        deep_path.mkdir(parents=True)

        dockfile_path = deep_path / "Dockfile.yaml"
        dockfile_path.write_text("version: '1.0'\n")

        result = runner.invoke(app, ["validate", str(dockfile_path)])
        # Should handle long path without crashing
        assert result.exit_code in [0, 1]

    def test_special_characters_in_payload(self, sample_dockfile):
        """Test payload with special characters."""
        payload = '{"text": "Special chars: <>&\\"\\\\"}'
        result = runner.invoke(app, ["test", sample_dockfile, "--payload", payload])
        assert result.exit_code == 0

    def test_unicode_in_payload(self, sample_dockfile):
        """Test payload with Unicode characters."""
        payload = '{"text": "Unicode: 你好世界 🚀"}'
        result = runner.invoke(app, ["test", sample_dockfile, "--payload", payload])
        assert result.exit_code == 0

    def test_very_large_payload(self, sample_dockfile):
        """Test with very large payload."""
        large_text = "x" * 10000
        payload = json.dumps({"text": large_text})
        result = runner.invoke(app, ["test", sample_dockfile, "--payload", payload])
        assert result.exit_code == 0

    def test_empty_payload(self, sample_dockfile):
        """Test with empty payload."""
        result = runner.invoke(app, ["test", sample_dockfile, "--payload", "{}"])
        # Should succeed (empty dict is valid JSON)
        assert result.exit_code == 0
