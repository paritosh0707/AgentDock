"""
Local Invocation Module
=======================

Provides functionality for invoking agents locally without a server:
- Direct agent invocation for testing
- Module path setup
- Error handling
"""

from pathlib import Path
from typing import Any, Dict, Optional

from dockrion_adapters import get_adapter
from dockrion_common import setup_module_path
from dockrion_common.errors import DockrionError

from .loader import load_dockspec


def invoke_local(
    dockfile_path: str, payload: Dict[str, Any], env_file: Optional[str] = None
) -> Dict[str, Any]:
    """Invoke an agent locally without starting a server.

    This is useful for:
    - Testing agents during development
    - Running one-off agent invocations
    - Integration testing

    Args:
        dockfile_path: Path to the Dockfile
        payload: Input data to pass to the agent
        env_file: Optional explicit path to .env file

    Returns:
        Agent response as a dictionary

    Raises:
        ValidationError: If Dockfile is invalid
        DockrionError: If agent loading or invocation fails
        MissingSecretError: If required secrets are missing

    Example:
        >>> result = invoke_local("Dockfile.yaml", {
        ...     "document_text": "INVOICE #123...",
        ...     "currency_hint": "USD"
        ... })
        >>> print(result["vendor"])
        Acme Corp
    """
    # Load and validate Dockfile (with env resolution)
    spec = load_dockspec(dockfile_path, env_file=env_file)

    # Setup Python path for agent module imports
    # This finds and adds the directory containing the agent's module to sys.path
    module_path = spec.agent.handler or spec.agent.entrypoint
    if module_path:
        dockfile_dir = Path(dockfile_path).resolve().parent
        setup_module_path(module_path, dockfile_dir)

    # Get the appropriate adapter for the framework
    framework = spec.agent.framework or "langgraph"  # Default to langgraph
    try:
        adapter = get_adapter(framework)
    except Exception as e:
        raise DockrionError(f"Failed to get adapter for framework '{framework}': {str(e)}")

    # Load the agent (entrypoint or handler mode)
    try:
        if spec.agent.handler:
            # Handler mode: load direct callable
            adapter.load(spec.agent.handler)
        elif spec.agent.entrypoint:
            # Entrypoint mode: load framework agent factory
            adapter.load(spec.agent.entrypoint)
        else:
            raise DockrionError("Agent must have either 'handler' or 'entrypoint' specified")
    except Exception as e:
        entrypoint_or_handler = spec.agent.handler or spec.agent.entrypoint
        raise DockrionError(
            f"Failed to load agent from '{entrypoint_or_handler}': {str(e)}\n"
            f"Make sure the module path is correct and the agent is properly implemented."
        )

    # Invoke the agent
    try:
        result = adapter.invoke(payload)
        return result
    except Exception as e:
        raise DockrionError(
            f"Agent invocation failed: {str(e)}\nCheck the agent implementation and input payload."
        )


__all__ = [
    "invoke_local",
]
