"""Tests for deploy.py module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dockrion_sdk.deploy import (
    deploy,
    run_local,
    _generate_requirements,
    _render_dockerfile,
    _render_runtime
)
from dockrion_schema.dockfile_v1 import DockSpec
from dockrion_common.errors import DockrionError


class TestGenerateRequirements:
    """Tests for _generate_requirements function."""
    
    def test_generate_requirements_langgraph(self, sample_dockfile):
        """Test requirements generation for LangGraph agent."""
        from dockrion_sdk.client import load_dockspec
        spec = load_dockspec(sample_dockfile)
        requirements = _generate_requirements(spec)
        
        assert "fastapi" in requirements
        assert "uvicorn" in requirements
        assert "prometheus-client" in requirements
        assert "dockrion-adapters" in requirements
        assert "langgraph" in requirements
    
    def test_generate_requirements_langchain(self, tmp_path):
        """Test requirements generation for LangChain agent."""
        from dockrion_sdk.client import load_dockspec
        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: langchain-agent
  entrypoint: app:build
  framework: langchain
model:
  provider: openai
  name: gpt-4
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
""")
        spec = load_dockspec(str(dockfile))
        requirements = _generate_requirements(spec)
        
        assert "langchain" in requirements
        assert "fastapi" in requirements


class TestRenderDockerfile:
    """Tests for _render_dockerfile function."""
    
    def test_render_dockerfile_basic(self, sample_dockfile):
        """Test Dockerfile generation."""
        from dockrion_sdk.client import load_dockspec
        spec = load_dockspec(sample_dockfile)
        dockerfile = _render_dockerfile(spec)
        
        assert "FROM python:" in dockerfile
        assert "WORKDIR /app" in dockerfile
        assert "EXPOSE 8080" in dockerfile
        assert "uvicorn" in dockerfile
    
    def test_render_dockerfile_custom_port(self, tmp_path):
        """Test Dockerfile with custom port."""
        from dockrion_sdk.client import load_dockspec
        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: custom-port-agent
  entrypoint: app:build
  framework: langgraph
model:
  provider: openai
  name: gpt-4
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 9000
""")
        spec = load_dockspec(str(dockfile))
        dockerfile = _render_dockerfile(spec)
        
        assert "EXPOSE 9000" in dockerfile
        assert "9000" in dockerfile


class TestRenderRuntime:
    """Tests for _render_runtime function."""
    
    def test_render_runtime_basic(self, sample_dockfile):
        """Test runtime code generation."""
        from dockrion_sdk.client import load_dockspec
        spec = load_dockspec(sample_dockfile)
        runtime = _render_runtime(spec)
        
        assert "from fastapi import FastAPI" in runtime
        assert "get_adapter" in runtime
        assert "@app.get(\"/health\")" in runtime
        assert "@app.post(\"/invoke\")" in runtime
        assert "@app.get(\"/schema\")" in runtime
        assert "@app.get(\"/metrics\")" in runtime
    
    def test_render_runtime_with_policies(self, tmp_path):
        """Test runtime generation with policies."""
        from dockrion_sdk.client import load_dockspec
        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text("""
version: "1.0"
agent:
  name: policy-agent
  entrypoint: app:build
  framework: langgraph
model:
  provider: openai
  name: gpt-4
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
        runtime = _render_runtime(spec)
        
        assert "apply_policies" in runtime


class TestDeploy:
    """Tests for deploy function."""
    
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_deploy_success(self, mock_check_call, mock_check_output, sample_dockfile):
        """Test successful deployment."""
        mock_check_output.return_value = "Docker version 20.10.0"
        mock_check_call.return_value = 0
        
        result = deploy(sample_dockfile, target="local")
        
        assert result["status"] == "built"
        assert "dockrion/" in result["image"]
        assert result["agent_name"] == "test-agent"
        mock_check_output.assert_called_once()
        mock_check_call.assert_called_once()
    
    @patch('subprocess.check_output')
    def test_deploy_docker_not_available(self, mock_check_output, sample_dockfile):
        """Test deployment when Docker is not available."""
        mock_check_output.side_effect = FileNotFoundError()
        
        with pytest.raises(DockrionError) as exc_info:
            deploy(sample_dockfile, target="local")
        assert "docker" in str(exc_info.value).lower()
    
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_deploy_build_failure(self, mock_check_call, mock_check_output, sample_dockfile):
        """Test deployment when Docker build fails."""
        import subprocess
        mock_check_output.return_value = "Docker version 20.10.0"
        mock_check_call.side_effect = subprocess.CalledProcessError(1, "docker build")
        
        with pytest.raises(DockrionError):
            deploy(sample_dockfile, target="local")


class TestRunLocal:
    """Tests for run_local function."""
    
    @patch('subprocess.Popen')
    @patch('subprocess.check_call')
    def test_run_local_success(self, mock_check_call, mock_popen, sample_dockfile, tmp_path, monkeypatch):
        """Test running agent locally."""
        # Change to tmp directory
        monkeypatch.chdir(tmp_path)
        
        mock_process = Mock()
        mock_popen.return_value = mock_process
        mock_check_call.return_value = 0
        
        proc = run_local(sample_dockfile)
        
        assert proc is mock_process
        # Check that runtime directory was created
        assert (tmp_path / ".dockrion_runtime").exists()
        assert (tmp_path / ".dockrion_runtime" / "main.py").exists()
        assert (tmp_path / ".dockrion_runtime" / "requirements.txt").exists()
    
    @patch('subprocess.check_call')
    def test_run_local_install_failure(self, mock_check_call, sample_dockfile, tmp_path, monkeypatch):
        """Test run_local when dependency installation fails."""
        import subprocess
        monkeypatch.chdir(tmp_path)
        mock_check_call.side_effect = subprocess.CalledProcessError(1, "pip install")
        
        with pytest.raises(DockrionError) as exc_info:
            run_local(sample_dockfile)
        assert "dependencies" in str(exc_info.value).lower() or "install" in str(exc_info.value).lower()

