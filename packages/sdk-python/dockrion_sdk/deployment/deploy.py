"""
Dockrion Deployment Module
==========================

Provides deployment functionality for Dockrion agents:
- Local development with hot reload
- Docker image building
- Runtime generation

Uses the template system for generating all deployment artifacts.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dockrion_common.errors import DockrionError
from dockrion_common.logger import get_logger

from ..core.loader import load_dockspec
from ..templates import TemplateRenderer
from ..utils.package_manager import (
    check_uv_available,
    install_requirements,
    print_uv_setup_instructions,
)
from ..utils.workspace import find_workspace_root, get_relative_agent_path
from .docker import check_docker_available, docker_build
from .pypi_server import DEFAULT_PYPI_PORT, check_local_pypi_available, get_local_pypi_url
from .runtime_gen import ensure_runtime_dir, write_runtime_files

logger = get_logger(__name__)

# ============================================================================
# Constants
# ============================================================================

DOCKRION_IMAGE_PREFIX = "dockrion"


# ============================================================================
# Main Deployment Functions
# ============================================================================


def deploy(
    dockfile_path: str,
    target: str = "local",
    tag: str = "dev",
    no_cache: bool = False,
    env_file: Optional[str] = None,
    allow_missing_secrets: bool = False,
    use_local_dockrion_packages: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Deploy an agent to a target environment.

    V1 Implementation: Builds a Docker image locally using uv package manager
    V1.1+: Will support remote deployment via Controller

    Args:
        dockfile_path: Path to the Dockfile
        target: Deployment target ("local" for V1)
        tag: Docker image tag (default: "dev")
        no_cache: If True, build without Docker cache
        env_file: Optional explicit path to .env file
        allow_missing_secrets: If True, continue even if required secrets are missing
        use_local_dockrion_packages: If True, install Dockrion packages from local
            PyPI server (for framework development only)
        **kwargs: Additional deployment options

    Returns:
        Dictionary with deployment information:
        {
            "image": str,  # Docker image name
            "status": str,  # "built" or "failed"
            "agent_name": str
        }

    Raises:
        DockrionError: If deployment fails
        MissingSecretError: If required secrets are missing and allow_missing_secrets=False

    Example:
        >>> result = deploy("Dockfile.yaml", target="local")
        >>> print(result["image"])
        dockrion/invoice-copilot:dev
    """
    # Check prerequisites
    if not check_uv_available():
        print_uv_setup_instructions()
        print("ℹ️  Continuing with Docker build (uv will be installed in container)...\n")

    if not check_docker_available():
        raise DockrionError(
            "Docker is not available. Please install Docker to deploy agents.\n"
            "Visit: https://docs.docker.com/get-docker/"
        )

    # Load and validate Dockfile (with env resolution)
    logger.info(f"Loading Dockfile: {dockfile_path}")
    try:
        spec = load_dockspec(
            dockfile_path,
            env_file=env_file,
            validate_secrets=True,
            strict_secrets=not allow_missing_secrets,
        )
    except Exception as e:
        raise DockrionError(f"Failed to load Dockfile: {str(e)}")

    logger.info(f"Agent: {spec.agent.name} ({spec.agent.framework})")

    # Initialize template renderer
    renderer = TemplateRenderer()

    # Create runtime directory and generate files
    runtime_dir = ensure_runtime_dir()
    write_runtime_files(spec, runtime_dir, renderer)

    # Build Docker image
    image = f"{DOCKRION_IMAGE_PREFIX}/{spec.agent.name}:{tag}"
    logger.info(f"Building Docker image: {image}")

    # Find workspace root for Docker build context
    agent_dir = Path.cwd()
    workspace_root = find_workspace_root(agent_dir)

    if workspace_root:
        # We're in a monorepo - use workspace root as build context
        relative_agent_path = get_relative_agent_path(workspace_root, agent_dir)
        build_context = str(workspace_root)
        logger.info(f"Using workspace root as build context: {workspace_root}")
        logger.debug(f"Agent relative path: {relative_agent_path}")
    else:
        # Standalone agent - use current directory
        relative_agent_path = "."
        build_context = "."
        logger.info("No workspace root found, using current directory as build context")

    # Handle local PyPI server mode (for framework developers)
    local_pypi_url = None
    if use_local_dockrion_packages:
        pypi_port = int(os.environ.get("DOCKRION_LOCAL_PYPI_PORT", DEFAULT_PYPI_PORT))
        if not check_local_pypi_available(pypi_port):
            raise DockrionError(
                f"Local PyPI server not running on port {pypi_port}.\n"
                "Start it first with: make pypi-local\n"
                "Or set DOCKRION_LOCAL_PYPI_PORT if using a different port."
            )
        local_pypi_url = get_local_pypi_url(pypi_port)
        logger.info(f"Using local PyPI server at {local_pypi_url}")

    try:
        # Generate Dockerfile with correct paths
        dockerfile_content = renderer.render_dockerfile(
            spec,
            agent_path=relative_agent_path,
            local_pypi_url=local_pypi_url,
            project_root=agent_dir,
        )

        # Build the image
        docker_build(
            image=image,
            dockerfile_content=dockerfile_content,
            build_context=build_context,
            no_cache=no_cache,
        )

    except DockrionError:
        raise
    except Exception as e:
        raise DockrionError(f"Docker build failed for agent '{spec.agent.name}'.\nError: {str(e)}")

    return {
        "image": image,
        "status": "built",
        "agent_name": spec.agent.name,
        "runtime_dir": str(runtime_dir),
    }


def run_local(
    dockfile_path: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: bool = False,
    env_file: Optional[str] = None,
) -> subprocess.Popen:
    """
    Run an agent locally without Docker (development mode).

    This function:
    1. Loads the Dockfile (with env resolution)
    2. Generates a FastAPI runtime using templates
    3. Installs dependencies
    4. Starts the server with uvicorn

    Args:
        dockfile_path: Path to the Dockfile
        host: Override host (default from Dockfile or 0.0.0.0)
        port: Override port (default from Dockfile or 8080)
        reload: Enable hot reload for development
        env_file: Optional explicit path to .env file

    Returns:
        subprocess.Popen object (running server)

    Raises:
        DockrionError: If startup fails
        MissingSecretError: If required secrets are missing

    Example:
        >>> proc = run_local("Dockfile.yaml", reload=True)
        >>> # Server is now running with hot reload...
        >>> proc.terminate()  # Stop the server
    """
    # Load and validate Dockfile (with env resolution)
    logger.info(f"Loading Dockfile: {dockfile_path}")
    try:
        spec = load_dockspec(dockfile_path, env_file=env_file)
    except Exception as e:
        raise DockrionError(f"Failed to load Dockfile: {str(e)}")

    logger.info(f"Agent: {spec.agent.name} ({spec.agent.framework})")

    # Initialize template renderer
    renderer = TemplateRenderer()

    # Create runtime directory and generate files
    runtime_dir = ensure_runtime_dir()
    write_runtime_files(spec, runtime_dir, renderer)

    # Determine host and port
    server_host = host or (spec.expose.host if spec.expose else "0.0.0.0")
    server_port = port or (spec.expose.port if spec.expose else 8080)

    # Install dependencies
    logger.info("Installing dependencies...")
    install_requirements(runtime_dir)

    # Build uvicorn command
    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        str(server_host),
        "--port",
        str(server_port),
    ]

    if reload:
        uvicorn_cmd.append("--reload")

    # Start the server
    logger.info(f"🚀 Starting agent server at http://{server_host}:{server_port}")

    try:
        proc = subprocess.Popen(uvicorn_cmd, cwd=str(runtime_dir))
        return proc
    except Exception as e:
        raise DockrionError(f"Failed to start server: {str(e)}")


def generate_runtime(
    dockfile_path: str,
    output_dir: Optional[str] = None,
    include_dockerfile: bool = True,
    env_file: Optional[str] = None,
) -> Dict[str, Path]:
    """
    Generate runtime files without building or running.

    Useful for inspection, customization, or CI/CD pipelines.

    Args:
        dockfile_path: Path to the Dockfile
        output_dir: Output directory (default: .dockrion_runtime)
        include_dockerfile: Include Dockerfile in output
        env_file: Optional explicit path to .env file

    Returns:
        Dictionary mapping file names to their paths

    Example:
        >>> files = generate_runtime("Dockfile.yaml", output_dir="./build")
        >>> print(files["main.py"])
        PosixPath('build/main.py')
    """
    # Load spec (with env resolution, non-strict for generation)
    logger.info(f"Loading Dockfile: {dockfile_path}")
    try:
        spec = load_dockspec(dockfile_path, env_file=env_file, strict_secrets=False)
    except Exception as e:
        raise DockrionError(f"Failed to load Dockfile: {str(e)}")

    # Determine output directory
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        out_path = ensure_runtime_dir()

    # Initialize renderer
    renderer = TemplateRenderer()

    # Generate files
    files = write_runtime_files(spec, out_path, renderer)

    # Optionally include Dockerfile
    if include_dockerfile:
        dockerfile_content = renderer.render_dockerfile(spec)
        dockerfile_path = out_path / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
        files["Dockerfile"] = dockerfile_path
        logger.debug(f"Written: {dockerfile_path}")

    logger.info(f"✅ Generated {len(files)} files in {out_path}")

    return files


__all__ = [
    "deploy",
    "run_local",
    "generate_runtime",
    "DOCKRION_IMAGE_PREFIX",
]
