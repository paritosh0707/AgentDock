"""
Docker Operations Module
=========================

Provides Docker-related functionality for Dockrion:
- Checking Docker availability
- Running containers
- Stopping containers
- Retrieving container logs
- Building images
"""

import subprocess
from typing import Dict, Optional

from dockrion_common.errors import DockrionError
from dockrion_common.logger import get_logger

logger = get_logger(__name__)


def check_docker_available() -> bool:
    """
    Check if Docker is available on the system.

    Returns:
        True if Docker is available, False otherwise
    """
    try:
        subprocess.check_output(["docker", "--version"], stderr=subprocess.STDOUT, text=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def docker_run(
    image: str,
    port: int = 8080,
    env_vars: Optional[Dict[str, str]] = None,
    detach: bool = True,
    name: Optional[str] = None,
) -> str:
    """
    Run a Docker image.

    Args:
        image: Docker image name
        port: Port to expose
        env_vars: Environment variables to pass
        detach: Run in detached mode
        name: Container name

    Returns:
        Container ID

    Raises:
        DockrionError: If docker run fails
    """
    cmd = ["docker", "run"]

    if detach:
        cmd.append("-d")

    if name:
        cmd.extend(["--name", name])

    cmd.extend(["-p", f"{port}:{port}"])

    if env_vars:
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])

    cmd.append(image)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        logger.info(f"Container started: {container_id[:12]}")
        return container_id

    except subprocess.CalledProcessError as e:
        raise DockrionError(f"Failed to run container: {e.stderr}")


def docker_stop(container: str) -> bool:
    """
    Stop a running Docker container.

    Args:
        container: Container ID or name

    Returns:
        True if stopped successfully
    """
    try:
        subprocess.run(["docker", "stop", container], capture_output=True, check=True)
        logger.info(f"Container stopped: {container}")
        return True
    except subprocess.CalledProcessError:
        logger.warning(f"Failed to stop container: {container}")
        return False


def docker_logs(container: str, follow: bool = False, tail: Optional[int] = None) -> str:
    """
    Get logs from a Docker container.

    Args:
        container: Container ID or name
        follow: Follow log output
        tail: Number of lines to show from end

    Returns:
        Log output as string
    """
    cmd = ["docker", "logs"]

    if follow:
        cmd.append("-f")

    if tail:
        cmd.extend(["--tail", str(tail)])

    cmd.append(container)

    if follow:
        # For follow mode, use Popen
        subprocess.Popen(cmd)
        return ""
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout + result.stderr


def docker_build(
    image: str, dockerfile_content: str, build_context: str, no_cache: bool = False
) -> None:
    """
    Build a Docker image from Dockerfile content.

    Args:
        image: Image name and tag
        dockerfile_content: Dockerfile content as string
        build_context: Directory to use as build context
        no_cache: If True, build without Docker cache

    Raises:
        DockrionError: If build fails
    """
    build_cmd = ["docker", "build", "-t", image, "-f", "-", "."]
    if no_cache:
        build_cmd.insert(2, "--no-cache")

    try:
        subprocess.run(
            build_cmd,
            input=dockerfile_content.encode(),
            cwd=build_context,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        logger.info(f"✅ Docker image built successfully: {image}")

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        logger.error(f"Docker build failed: {stderr}")
        raise DockrionError(f"Docker build failed.\nError: {stderr}")


__all__ = [
    "check_docker_available",
    "docker_run",
    "docker_stop",
    "docker_logs",
    "docker_build",
]
