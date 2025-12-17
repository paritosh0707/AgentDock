import os
import re
import time
import yaml
from pathlib import Path
from typing import Dict, Any
from dockrion_schema.dockfile_v1 import DockSpec
from dockrion_common.errors import ValidationError, DockrionError
from dockrion_adapters import get_adapter


def expand_env_vars(data: Any) -> Any:
    """Recursively expand ${VAR} and ${VAR:-default} in dict/list values.
    
    Args:
        data: Dictionary, list, string, or other value to process
        
    Returns:
        Data with environment variables expanded
        
    Raises:
        ValidationError: If required environment variable is missing
        
    Examples:
        >>> os.environ["FOO"] = "bar"
        >>> expand_env_vars({"key": "${FOO}"})
        {"key": "bar"}
        >>> expand_env_vars({"key": "${MISSING:-default}"})
        {"key": "default"}
    """
    if isinstance(data, dict):
        return {key: expand_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [expand_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Pattern: ${VAR} or ${VAR:-default}
        pattern = r'\$\{([^}:]+)(?::-)?(([^}]*))?\}'
        
        def replacer(match):
            var_name = match.group(1)
            # Group 2 may be empty string or None when no default is provided
            default_value = match.group(2) if match.group(2) else None
            
            if var_name in os.environ:
                return os.environ[var_name]
            elif default_value:
                return default_value
            else:
                raise ValidationError(
                    f"Environment variable '${{{var_name}}}' is required but not set. "
                    f"Either set the variable or use ${{VAR:-default}} syntax for a default value."
                )
        
        return re.sub(pattern, replacer, data)
    else:
        return data


def load_dockspec(path: str) -> DockSpec:
    """Load and validate a Dockfile from the filesystem.
    
    This function:
    1. Checks if the file exists
    2. Reads and parses the YAML file
    3. Expands environment variables (${VAR} syntax)
    4. Validates the structure using DockSpec schema
    
    Args:
        path: Path to the Dockfile (typically "Dockfile.yaml")
        
    Returns:
        Validated DockSpec object
        
    Raises:
        ValidationError: If file not found, invalid YAML, or schema validation fails
        
    Example:
        >>> spec = load_dockspec("Dockfile.yaml")
        >>> print(spec.agent.name)
        invoice-copilot
    """
    file_path = Path(path)
    
    # Check if file exists
    if not file_path.exists():
        raise ValidationError(
            f"Dockfile not found: {path}\n"
            f"Make sure the file exists and the path is correct."
        )
    
    # Read and parse YAML
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValidationError(
            f"Invalid YAML in Dockfile: {path}\n"
            f"Error: {str(e)}\n"
            f"Please check the YAML syntax."
        )
    except Exception as e:
        raise ValidationError(
            f"Failed to read Dockfile: {path}\n"
            f"Error: {str(e)}"
        )
    
    if data is None:
        raise ValidationError(
            f"Dockfile is empty: {path}\n"
            f"Please add valid configuration."
        )
    
    # Expand environment variables
    try:
        data = expand_env_vars(data)
    except ValidationError:
        # Re-raise ValidationError as-is
        raise
    except Exception as e:
        raise ValidationError(
            f"Failed to expand environment variables in Dockfile: {path}\n"
            f"Error: {str(e)}"
        )
    
    # Validate against schema
    try:
        return DockSpec.model_validate(data)
    except Exception as e:
        raise ValidationError(
            f"Invalid Dockfile structure: {path}\n"
            f"Error: {str(e)}\n"
            f"Please check the Dockfile format against the schema."
        )


def invoke_local(dockfile_path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke an agent locally without starting a server.
    
    This is useful for:
    - Testing agents during development
    - Running one-off agent invocations
    - Integration testing
    
    Args:
        dockfile_path: Path to the Dockfile
        payload: Input data to pass to the agent
        
    Returns:
        Agent response as a dictionary
        
    Raises:
        ValidationError: If Dockfile is invalid
        DockrionError: If agent loading or invocation fails
        
    Example:
        >>> result = invoke_local("Dockfile.yaml", {
        ...     "document_text": "INVOICE #123...",
        ...     "currency_hint": "USD"
        ... })
        >>> print(result["vendor"])
        Acme Corp
    """
    # Load and validate Dockfile
    spec = load_dockspec(dockfile_path)
    
    # Get the appropriate adapter for the framework
    try:
        adapter = get_adapter(spec.agent.framework)
    except Exception as e:
        raise DockrionError(
            f"Failed to get adapter for framework '{spec.agent.framework}': {str(e)}"
        )
    
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
            f"Agent invocation failed: {str(e)}\n"
            f"Check the agent implementation and input payload."
        )


# In v1 this is a placeholder; v1.1+ will talk to Controller service.
class ControllerClient:
    """Client for interacting with the dockrion Controller service.
    
    Note: V1 implementation is a placeholder. V1.1+ will provide full
    functionality for remote deployments, agent management, and monitoring.
    """
    
    def __init__(self, base_url: str | None = None):
        """Initialize controller client.
        
        Args:
            base_url: Base URL of the controller service (e.g., "http://localhost:8000")
        """
        self.base_url = base_url or "http://localhost:8000"

    def status(self) -> Dict[str, Any]:
        """Get controller status.
        
        Returns:
            Status information including timestamp
        """
        return {"ok": True, "ts": time.time()}
