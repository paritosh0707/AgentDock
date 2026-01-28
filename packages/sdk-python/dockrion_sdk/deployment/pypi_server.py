"""
Local PyPI Server Module
========================

Provides functionality for running a local PyPI server during development builds.
This allows Docker builds to install local Dockrion packages from the monorepo.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from dockrion_common.errors import DockrionError
from dockrion_common.logger import get_logger

logger = get_logger(__name__)

# Default port for local PyPI server
DEFAULT_PYPI_PORT = 8099


def find_available_port(start_port: int = DEFAULT_PYPI_PORT) -> int:
    """
    Find an available port starting from start_port.

    Args:
        start_port: Port to start searching from

    Returns:
        Available port number

    Raises:
        DockrionError: If no port found in range
    """
    port = start_port
    while port < start_port + 100:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            port += 1
    raise DockrionError(f"Could not find available port in range {start_port}-{start_port + 100}")


def start_local_pypi_server(dist_dir: Path) -> Tuple[subprocess.Popen, int]:
    """
    Start a local PyPI server serving wheels from dist_dir.

    Args:
        dist_dir: Directory containing wheel files

    Returns:
        Tuple of (server process, port)

    Raises:
        DockrionError: If server fails to start
    """
    port = find_available_port(DEFAULT_PYPI_PORT)

    # Start pypiserver
    cmd = [sys.executable, "-m", "pypiserver", "run", "-p", str(port), str(dist_dir)]

    logger.info(f"Starting local PyPI server on port {port}...")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for server to be ready
    max_retries = 30
    for _ in range(max_retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", port))
                logger.info(f"Local PyPI server ready on port {port}")
                return proc, port
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.1)

    # If we get here, server didn't start
    proc.terminate()
    raise DockrionError("Failed to start local PyPI server")


def stop_local_pypi_server(proc: Optional[subprocess.Popen]) -> None:
    """
    Stop the local PyPI server.

    Args:
        proc: Server process to stop
    """
    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        logger.info("Local PyPI server stopped")


def get_local_pypi_url(port: int) -> str:
    """
    Get the URL for the local PyPI server accessible from Docker.

    Uses host.docker.internal for Mac/Windows Docker.

    Args:
        port: Port the server is running on

    Returns:
        URL string for pip/uv to use
    """
    # Use host.docker.internal to access host from Docker (Mac/Windows)
    # For Linux, you may need to use --network=host or the host IP
    return f"http://host.docker.internal:{port}/simple/"


def check_local_pypi_available(port: int = DEFAULT_PYPI_PORT) -> bool:
    """
    Check if local PyPI server is running and accessible.

    Args:
        port: Port to check (default: DEFAULT_PYPI_PORT)

    Returns:
        True if server is accessible, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(("127.0.0.1", port))
            return True
    except (socket.error, ConnectionRefusedError):
        return False


__all__ = [
    "find_available_port",
    "start_local_pypi_server",
    "stop_local_pypi_server",
    "get_local_pypi_url",
    "check_local_pypi_available",
    "DEFAULT_PYPI_PORT",
]
