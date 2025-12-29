"""Tests for deployment module."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Ensure tests directory is in path for fixture imports
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

from dockrion_common.errors import DockrionError

from dockrion_sdk import (
    deploy,
    run_local,
)
from dockrion_sdk.templates import (
    render_dockerfile,
    render_requirements,
    render_runtime,
)


class TestGenerateRequirements:
    """Tests for render_requirements function."""

    def test_generate_requirements_langgraph(self, sample_dockfile):
        """Test requirements generation for LangGraph agent."""
        from dockrion_sdk import load_dockspec

        spec = load_dockspec(sample_dockfile)
        requirements = render_requirements(spec)

        assert "fastapi" in requirements
        assert "uvicorn" in requirements
        assert "prometheus-client" in requirements
        # langgraph requirements
        assert "langgraph" in requirements

    def test_generate_requirements_langchain(self, tmp_path):
        """Test requirements generation for LangChain agent."""
        from dockrion_sdk import load_dockspec

        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: langchain-agent
  entrypoint: app:build
  framework: langchain
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
""")
        spec = load_dockspec(str(dockfile))
        requirements = render_requirements(spec)

        assert "fastapi" in requirements


class TestRenderDockerfile:
    """Tests for render_dockerfile function."""

    def test_render_dockerfile_basic(self, sample_dockfile):
        """Test Dockerfile generation."""
        from dockrion_sdk import load_dockspec

        spec = load_dockspec(sample_dockfile)
        dockerfile = render_dockerfile(spec)

        assert "FROM python:" in dockerfile
        assert "WORKDIR /app" in dockerfile
        assert "EXPOSE 8080" in dockerfile
        assert "uvicorn" in dockerfile

    def test_render_dockerfile_custom_port(self, tmp_path):
        """Test Dockerfile with custom port."""
        from dockrion_sdk import load_dockspec

        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: custom-port-agent
  entrypoint: app:build
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 9000
""")
        spec = load_dockspec(str(dockfile))
        dockerfile = render_dockerfile(spec)

        assert "EXPOSE 9000" in dockerfile
        assert "9000" in dockerfile


class TestRenderRuntime:
    """Tests for render_runtime function."""

    def test_render_runtime_basic(self, sample_dockfile):
        """Test runtime code generation."""
        from dockrion_sdk import load_dockspec

        spec = load_dockspec(sample_dockfile)
        runtime = render_runtime(spec)

        # Check for key components - uses create_app pattern
        assert "create_app" in runtime
        assert "DockSpec" in runtime
        assert "uvicorn" in runtime

    def test_render_runtime_with_policies(self, tmp_path):
        """Test runtime generation with policies."""
        from dockrion_sdk import load_dockspec

        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: policy-agent
  entrypoint: app:build
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
policies:
  tools:
    allowed: [tool1, tool2]
  safety:
    redact_patterns: ["\\\\d{16}"]
expose:
  port: 8080
""")
        spec = load_dockspec(str(dockfile))
        runtime = render_runtime(spec)

        # Check runtime was generated
        assert "FastAPI" in runtime


class TestDeploy:
    """Tests for deploy function."""

    @patch("dockrion_sdk.deployment.deploy.docker_build")
    @patch("dockrion_sdk.deployment.deploy.check_docker_available")
    def test_deploy_success(
        self, mock_check_docker, mock_docker_build, sample_dockfile, tmp_path, monkeypatch
    ):
        """Test successful deployment."""
        monkeypatch.chdir(tmp_path)

        # Mock Docker available
        mock_check_docker.return_value = True

        # Mock Docker build to succeed
        mock_docker_build.return_value = None

        result = deploy(sample_dockfile, target="local")

        assert result["status"] == "built"
        assert "dockrion/" in result["image"]
        assert result["agent_name"] == "test-agent"
        mock_docker_build.assert_called_once()

    @patch("subprocess.check_output")
    def test_deploy_docker_not_available(self, mock_check_output, sample_dockfile):
        """Test deployment when Docker is not available."""
        mock_check_output.side_effect = FileNotFoundError()

        with pytest.raises(DockrionError) as exc_info:
            deploy(sample_dockfile, target="local")
        assert "docker" in str(exc_info.value).lower()

    @patch("subprocess.check_output")
    @patch("subprocess.check_call")
    def test_deploy_build_failure(self, mock_check_call, mock_check_output, sample_dockfile):
        """Test deployment when Docker build fails."""
        import subprocess

        mock_check_output.return_value = "Docker version 20.10.0"
        mock_check_call.side_effect = subprocess.CalledProcessError(1, "docker build")

        with pytest.raises(DockrionError):
            deploy(sample_dockfile, target="local")


class TestRunLocal:
    """Tests for run_local function."""

    @patch("dockrion_sdk.deployment.deploy.subprocess.Popen")
    @patch("dockrion_sdk.deployment.deploy.install_requirements")
    def test_run_local_success(
        self, mock_install, mock_popen, sample_dockfile, tmp_path, monkeypatch
    ):
        """Test running agent locally."""
        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        mock_install.return_value = None  # Install succeeds

        proc = run_local(sample_dockfile)

        # Check that runtime directory was created
        assert (tmp_path / ".dockrion_runtime").exists()
        assert (tmp_path / ".dockrion_runtime" / "main.py").exists()
        assert (tmp_path / ".dockrion_runtime" / "requirements.txt").exists()
        assert proc is mock_process
        mock_install.assert_called_once()
        mock_popen.assert_called_once()

    @patch("dockrion_sdk.deployment.deploy.install_requirements")
    def test_run_local_install_failure(self, mock_install, sample_dockfile, tmp_path, monkeypatch):
        """Test run_local when dependency installation fails."""
        monkeypatch.chdir(tmp_path)
        mock_install.side_effect = DockrionError("Failed to install dependencies")

        with pytest.raises(DockrionError) as exc_info:
            run_local(sample_dockfile)
        assert (
            "dependencies" in str(exc_info.value).lower()
            or "install" in str(exc_info.value).lower()
            or "failed" in str(exc_info.value).lower()
        )
