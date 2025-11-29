import os
from pathlib import Path
from typing import List, Optional, Generator


def get_local_logs(agent_name: str, lines: int = 100) -> List[str]:
    """Get logs from a locally running agent.
    
    V1 Implementation: Reads from .dockrion_runtime/logs/ directory
    V1.1+: Will query Controller API for remote agent logs
    
    Args:
        agent_name: Name of the agent
        lines: Number of log lines to retrieve (default: 100)
        
    Returns:
        List of log lines (most recent first)
        
    Example:
        >>> logs = get_local_logs("invoice-copilot", lines=50)
        >>> for line in logs:
        ...     print(line)
    """
    # V1: Simple file-based logging
    log_dir = Path(".dockrion_runtime") / "logs"
    log_file = log_dir / f"{agent_name}.log"
    
    if not log_file.exists():
        return [f"No logs found for agent '{agent_name}'"]
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            # Return last N lines
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception as e:
        return [f"Error reading logs: {str(e)}"]


def tail_build_logs(build_id: str) -> Generator[str, None, None]:
    """Stream build logs in real-time (generator).
    
    V1 Implementation: Placeholder that yields sample messages
    V1.1+: Will stream real build logs from Controller
    
    Args:
        build_id: Build identifier
        
    Yields:
        Log lines as they become available
        
    Example:
        >>> for log_line in tail_build_logs("build-123"):
        ...     print(log_line)
    """
    # V1: Placeholder implementation
    yield f"Build {build_id} started"
    yield "Pulling base image..."
    yield "Installing dependencies..."
    yield "Building agent runtime..."
    yield "Build complete"


def stream_agent_logs(agent_name: str, follow: bool = False) -> Generator[str, None, None]:
    """Stream agent logs (optionally follow for real-time updates).
    
    V1 Implementation: Reads existing logs
    V1.1+: Will support real-time log streaming
    
    Args:
        agent_name: Name of the agent
        follow: If True, continue streaming new logs as they arrive
        
    Yields:
        Log lines
        
    Example:
        >>> for log_line in stream_agent_logs("invoice-copilot"):
        ...     print(log_line)
    """
    logs = get_local_logs(agent_name, lines=1000)
    for line in logs:
        yield line.rstrip('\n')
    
    if follow:
        # V1: Not implemented, just return
        # V1.1+: Will use file watching or Controller streaming
        yield "[Follow mode not supported in V1]"
