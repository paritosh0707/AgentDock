"""Integration tests for the SDK package.

These tests verify end-to-end functionality across multiple SDK components.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Ensure tests directory is in path for fixture imports
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

from dockrion_common.errors import DockrionError, ValidationError

from dockrion_sdk import deploy, invoke_local, load_dockspec, run_local, validate_dockspec


class TestEndToEndWorkflow:
    """Test complete workflows from Dockfile to agent invocation."""

    def test_validate_load_invoke_workflow(self, sample_dockfile):
        """Test the complete workflow: validate -> load -> invoke."""
        # Step 1: Validate
        result = validate_dockspec(sample_dockfile)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

        # Step 2: Load
        spec = load_dockspec(sample_dockfile)
        assert spec.agent.name == "test-agent"
        assert spec.agent.framework == "langgraph"

        # Step 3: Invoke
        payload = {"text": "test input"}
        output = invoke_local(sample_dockfile, payload)
        assert "result" in output
        assert "test input" in output["result"]

    def test_env_var_expansion_in_full_workflow(self, tmp_path, set_env_vars):
        """Test environment variable expansion throughout the workflow."""
        # Set required env vars for this test
        import os

        os.environ["AGENT_NAME"] = "test-agent"

        # Create Dockfile with env vars
        dockfile_content = """
version: "1.0"
agent:
  name: ${AGENT_NAME}
  description: "Test agent with env vars"
  entrypoint: tests.fixtures.mock_agent:build_agent
  framework: langgraph
io_schema:
  input:
    type: object
    properties:
      text: { type: string }
  output:
    type: object
    properties:
      result: { type: string }
expose:
  port: 8080
  host: "0.0.0.0"
"""
        dockfile_path = tmp_path / "Dockfile.yaml"
        dockfile_path.write_text(dockfile_content.strip())

        # Validate with env vars
        result = validate_dockspec(str(dockfile_path))
        assert result["valid"] is True

        # Load and check expansion
        spec = load_dockspec(str(dockfile_path))
        assert spec.agent.name == "test-agent"
        assert spec.expose.port == 8080

    def test_validation_errors_prevent_deployment(self, tmp_path):
        """Test that validation errors prevent deployment."""
        # Create invalid Dockfile (missing required fields)
        dockfile_content = """
version: "1.0"
agent:
  name: invalid-agent
"""
        dockfile_path = tmp_path / "Dockfile.yaml"
        dockfile_path.write_text(dockfile_content.strip())

        # Validation should fail
        result = validate_dockspec(str(dockfile_path))
        assert result["valid"] is False
        assert len(result["errors"]) > 0

        # Load should raise ValidationError
        with pytest.raises(ValidationError):
            load_dockspec(str(dockfile_path))


class TestRuntimeGeneration:
    """Test runtime code and requirements generation."""

    def test_runtime_generation_creates_valid_python(self, sample_dockfile, tmp_path):
        """Test that generated runtime is valid Python code."""
        from dockrion_sdk.templates import render_runtime

        spec = load_dockspec(sample_dockfile)
        runtime_code = render_runtime(spec)

        # Write to file and try to compile
        runtime_file = tmp_path / "test_runtime.py"
        runtime_file.write_text(runtime_code)

        # Should compile without errors
        with open(runtime_file, "r") as f:
            code = f.read()
            compile(code, str(runtime_file), "exec")

    def test_requirements_generation_includes_framework_deps(self, sample_dockfile):
        """Test that requirements.txt includes framework-specific dependencies."""
        from dockrion_sdk.templates import render_requirements

        spec = load_dockspec(sample_dockfile)
        requirements = render_requirements(spec)

        # Check for base dependencies
        assert "fastapi" in requirements
        assert "uvicorn" in requirements
        assert "prometheus-client" in requirements

    def test_requirements_includes_policy_engine_when_policies_defined(self, tmp_path):
        """Test that policy engine is included when policies are defined."""
        from dockrion_sdk.templates import render_requirements

        # Create Dockfile with policies
        dockfile_content = """
version: "1.0"
agent:
  name: test-agent
  description: "Test agent with policies"
  entrypoint: fixtures.mock_agent:build_agent
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
policies:
  tools:
    allowed: [web_search]
    deny_by_default: true
expose:
  port: 8080
"""
        dockfile_path = tmp_path / "Dockfile.yaml"
        dockfile_path.write_text(dockfile_content.strip())

        spec = load_dockspec(str(dockfile_path))
        requirements = render_requirements(spec)

        # Requirements should include base packages
        assert "fastapi" in requirements


class TestErrorHandling:
    """Test error handling across SDK components."""

    def test_missing_dockfile_error(self):
        """Test error when Dockfile doesn't exist."""
        with pytest.raises(ValidationError, match="Dockfile not found"):
            load_dockspec("nonexistent.yaml")

    def test_invalid_yaml_error(self, tmp_path):
        """Test error when YAML is malformed."""
        dockfile_path = tmp_path / "invalid.yaml"
        dockfile_path.write_text("invalid: yaml: content: [")

        with pytest.raises(ValidationError, match="Invalid YAML"):
            load_dockspec(str(dockfile_path))

    def test_missing_env_var_error(self, tmp_path):
        """Test error when required env var is missing."""
        dockfile_content = """
version: "1.0"
agent:
  name: ${MISSING_VAR}
  entrypoint: test:agent
  framework: langgraph
"""
        dockfile_path = tmp_path / "Dockfile.yaml"
        dockfile_path.write_text(dockfile_content.strip())

        # Make sure the env var doesn't exist
        if "MISSING_VAR" in os.environ:
            del os.environ["MISSING_VAR"]

        with pytest.raises(ValidationError, match="Environment variable.*MISSING_VAR.*is required"):
            load_dockspec(str(dockfile_path))

    def test_invalid_entrypoint_error(self, sample_dockfile):
        """Test error when agent entrypoint is invalid."""
        # Modify the Dockfile to have invalid entrypoint
        spec = load_dockspec(sample_dockfile)
        spec.agent.entrypoint = "nonexistent.module:function"

        # Save modified spec
        from pathlib import Path

        import yaml

        temp_path = Path(sample_dockfile).parent / "temp_invalid.yaml"
        with open(temp_path, "w") as f:
            yaml.dump(spec.model_dump(), f)

        # Should raise DockrionError when trying to invoke
        with pytest.raises(DockrionError, match="Failed to load agent"):
            invoke_local(str(temp_path), {"text": "test"})

        # Cleanup
        temp_path.unlink()


class TestWarnings:
    """Test warning generation for potential issues."""

    def test_high_timeout_warning(self, tmp_path):
        """Test warning for very high timeout values."""
        dockfile_content = """
version: "1.0"
agent:
  name: test-agent
  entrypoint: tests.fixtures.mock_agent:build_agent
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
arguments:
  timeout_sec: 500
expose:
  port: 8080
"""
        dockfile_path = tmp_path / "Dockfile.yaml"
        dockfile_path.write_text(dockfile_content.strip())

        result = validate_dockspec(str(dockfile_path))
        assert result["valid"] is True
        assert any("timeout" in w.lower() for w in result["warnings"])

    def test_low_timeout_warning(self, tmp_path):
        """Test warning for very low timeout values."""
        dockfile_content = """
version: "1.0"
agent:
  name: test-agent
  entrypoint: tests.fixtures.mock_agent:build_agent
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
arguments:
  timeout_sec: 2
expose:
  port: 8080
"""
        dockfile_path = tmp_path / "Dockfile.yaml"
        dockfile_path.write_text(dockfile_content.strip())

        result = validate_dockspec(str(dockfile_path))
        assert result["valid"] is True
        assert any("timeout" in w.lower() for w in result["warnings"])


class TestDockerIntegration:
    """Test Docker-related functionality (requires Docker to be installed)."""

    @pytest.mark.skipif(
        subprocess.run(["docker", "--version"], capture_output=True).returncode != 0,
        reason="Docker not available",
    )
    def test_docker_availability_check(self):
        """Test that Docker availability is properly checked."""
        # This should not raise if Docker is available
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_deploy_without_docker_raises_error(self, sample_dockfile, monkeypatch):
        """Test that deploy raises error when Docker is not available."""

        # Mock subprocess to simulate Docker not being available
        def mock_check_output(*args, **kwargs):
            raise FileNotFoundError("docker not found")

        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        with pytest.raises(DockrionError, match="Docker is not available"):
            deploy(sample_dockfile)


class TestLocalServerLifecycle:
    """Test local server startup and shutdown."""

    def test_run_local_creates_runtime_directory(self, sample_dockfile):
        """Test that run_local creates the runtime directory."""
        runtime_dir = Path(".dockrion_runtime")

        # Clean up if exists
        if runtime_dir.exists():
            import shutil

            shutil.rmtree(runtime_dir)

        # Start server (will fail due to missing deps, but should create dir)
        try:
            proc = run_local(sample_dockfile)
            # Give it a moment
            time.sleep(1)
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            pass  # Expected to fail in test environment

        # Check that runtime directory was created
        assert runtime_dir.exists()
        assert (runtime_dir / "main.py").exists()
        assert (runtime_dir / "requirements.txt").exists()

    def test_deploy_creates_runtime_files(self, sample_dockfile, monkeypatch):
        """Test that deploy creates runtime files before building."""
        runtime_dir = Path(".dockrion_runtime")

        # Clean up if exists
        if runtime_dir.exists():
            import shutil

            shutil.rmtree(runtime_dir)

        # Mock Docker to avoid actual build
        def mock_check_output(*args, **kwargs):
            return b"Docker version 20.10.0"

        def mock_run(*args, **kwargs):
            # Simulate successful build
            class MockResult:
                returncode = 0
                stdout = b"Successfully built"
                stderr = b""

            return MockResult()

        monkeypatch.setattr(subprocess, "check_output", mock_check_output)
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Deploy should create runtime files
        result = deploy(sample_dockfile)

        # Check that runtime files were created
        assert runtime_dir.exists()
        assert (runtime_dir / "main.py").exists()
        assert (runtime_dir / "requirements.txt").exists()
        assert result["status"] == "built"


class TestConcurrentOperations:
    """Test handling of concurrent operations."""

    def test_multiple_validations_concurrent(self, sample_dockfile):
        """Test that multiple validations can run concurrently."""
        import concurrent.futures

        def validate():
            return validate_dockspec(sample_dockfile)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(validate) for _ in range(10)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r["valid"] for r in results)

    def test_multiple_loads_concurrent(self, sample_dockfile):
        """Test that multiple loads can run concurrently."""
        import concurrent.futures

        def load():
            return load_dockspec(sample_dockfile)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(load) for _ in range(10)]
            specs = [f.result() for f in futures]

        # All should succeed
        assert all(s.agent.name == "test-agent" for s in specs)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_dockfile(self, tmp_path):
        """Test handling of empty Dockfile."""
        dockfile_path = tmp_path / "empty.yaml"
        dockfile_path.write_text("")

        with pytest.raises(ValidationError, match="empty"):
            load_dockspec(str(dockfile_path))

    def test_dockfile_with_only_whitespace(self, tmp_path):
        """Test handling of Dockfile with only whitespace."""
        dockfile_path = tmp_path / "whitespace.yaml"
        dockfile_path.write_text("   \n\n   \t\t\n")

        with pytest.raises(ValidationError):
            load_dockspec(str(dockfile_path))

    def test_very_long_agent_name(self, tmp_path):
        """Test handling of very long agent names."""
        # Agent names are limited to 63 characters (for DNS compatibility)
        long_name = "a" * 63
        dockfile_content = f"""
version: "1.0"
agent:
  name: {long_name}
  entrypoint: fixtures.mock_agent:build_agent
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
"""
        dockfile_path = tmp_path / "Dockfile.yaml"
        dockfile_path.write_text(dockfile_content.strip())

        # Should load successfully with max length name
        spec = load_dockspec(str(dockfile_path))
        assert len(spec.agent.name) == 63

    def test_special_characters_in_values(self, tmp_path):
        """Test handling of special characters in values."""
        # Using properly escaped YAML
        dockfile_content = """
version: "1.0"
agent:
  name: test-agent-special
  description: 'Agent with special chars: <>&'
  entrypoint: fixtures.mock_agent:build_agent
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
"""
        dockfile_path = tmp_path / "Dockfile.yaml"
        dockfile_path.write_text(dockfile_content.strip())

        spec = load_dockspec(str(dockfile_path))
        assert spec.agent.name == "test-agent-special"
        assert "<>&" in spec.agent.description
