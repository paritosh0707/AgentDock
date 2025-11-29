"""dockrion SDK - Python SDK for deploying and managing AI agents.

This package provides tools for:
- Loading and validating Dockfiles
- Deploying agents locally or remotely
- Invoking agents programmatically
- Managing agent logs and monitoring

Example:
    >>> from dockrion_sdk import load_dockspec, invoke_local
    >>> spec = load_dockspec("Dockfile.yaml")
    >>> result = invoke_local("Dockfile.yaml", {"input": "data"})
"""

from .client import load_dockspec, invoke_local, ControllerClient, expand_env_vars
from .validate import validate_dockspec, validate
from .deploy import deploy, run_local
from .logs import get_local_logs, tail_build_logs, stream_agent_logs

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
    
    # Logs
    "get_local_logs",
    "tail_build_logs",
    "stream_agent_logs",
    
    # Client
    "ControllerClient",
]
