"""
Deployment Module
=================

Modules for building and deploying Dockrion agents:
- Docker image building
- Local development server
- Runtime file generation
- Local PyPI server for dev builds
"""

from .deploy import DOCKRION_IMAGE_PREFIX, deploy, generate_runtime, run_local
from .docker import check_docker_available, docker_build, docker_logs, docker_run, docker_stop
from .pypi_server import (
    find_available_port,
    get_local_pypi_url,
    start_local_pypi_server,
    stop_local_pypi_server,
)
from .runtime_gen import RUNTIME_DIR_NAME, clean_runtime, ensure_runtime_dir, write_runtime_files

__all__ = [
    # Main deployment functions
    "deploy",
    "run_local",
    "generate_runtime",
    "DOCKRION_IMAGE_PREFIX",
    # Docker operations
    "docker_run",
    "docker_stop",
    "docker_logs",
    "docker_build",
    "check_docker_available",
    # Runtime generation
    "ensure_runtime_dir",
    "write_runtime_files",
    "clean_runtime",
    "RUNTIME_DIR_NAME",
    # PyPI server
    "start_local_pypi_server",
    "stop_local_pypi_server",
    "find_available_port",
    "get_local_pypi_url",
]
