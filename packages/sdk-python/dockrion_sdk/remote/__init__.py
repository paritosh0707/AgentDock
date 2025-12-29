"""
Remote Services Module
======================

Modules for interacting with remote Dockrion services:
- Controller client for remote deployments
- Log retrieval and streaming
"""

from .controller import ControllerClient
from .logs import get_local_logs, stream_agent_logs, tail_build_logs

__all__ = [
    "ControllerClient",
    "get_local_logs",
    "tail_build_logs",
    "stream_agent_logs",
]
