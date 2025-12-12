"""Dockrion SDK - Python SDK for deploying and managing AI agents.

This package provides tools for:
- Loading and validating Dockfiles
- Deploying agents locally or via Docker
- Template-based runtime generation
- Invoking agents programmatically
- Managing agent logs and monitoring

Example:
    >>> from dockrion_sdk import load_dockspec, deploy, run_local
    >>> spec = load_dockspec("Dockfile.yaml")
    >>> result = deploy("Dockfile.yaml")  # Build Docker image
    >>> proc = run_local("Dockfile.yaml")  # Run locally for development
"""

from .client import load_dockspec, invoke_local, ControllerClient, expand_env_vars
from .validate import validate_dockspec, validate
from .deploy import deploy, run_local, generate_runtime, clean_runtime, docker_run, docker_stop
from .logs import get_local_logs, tail_build_logs, stream_agent_logs
from .templates import TemplateRenderer, render_runtime, render_dockerfile, render_requirements

__version__ = "0.1.0"

__all__ = [
    # Core functions
    "load_dockspec",
    "invoke_local",
    "expand_env_vars",
    
    # Validation
    "validate_dockspec",
    "validate",
    
    # Deployment
    "deploy",
    "run_local",
    "generate_runtime",
    "clean_runtime",
    "docker_run",
    "docker_stop",
    
    # Templates
    "TemplateRenderer",
    "render_runtime",
    "render_dockerfile",
    "render_requirements",
    
    # Logs
    "get_local_logs",
    "tail_build_logs",
    "stream_agent_logs",
    
    # Client
    "ControllerClient",
]
