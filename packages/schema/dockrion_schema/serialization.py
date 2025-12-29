"""
dockrion Schema Serialization Utilities

This module provides utilities for converting between DockSpec objects and
various formats (dict, YAML string).

IMPORTANT: These are PURE DATA TRANSFORMATIONS - NO FILE I/O
- to_dict(): DockSpec → dict
- to_yaml_string(): DockSpec → YAML string
- from_dict(): dict → DockSpec

File reading/writing is SDK's responsibility, not schema's.

Usage:
    from dockrion_schema import DockSpec, to_dict, to_yaml_string

    # Convert model to dict
    spec_dict = to_dict(spec)

    # Convert model to YAML string
    yaml_str = to_yaml_string(spec)

    # SDK would then write to file:
    # with open("Dockfile.yaml", "w") as f:
    #     f.write(yaml_str)
"""

from typing import Any, Dict

from .dockfile_v1 import DockSpec


def to_dict(spec: DockSpec, exclude_none: bool = True) -> Dict[str, Any]:
    """
    Convert DockSpec to plain Python dictionary.

    This is useful for serialization, API responses, or further processing.

    Args:
        spec: DockSpec object to convert
        exclude_none: If True, exclude fields with None values (default: True)

    Returns:
        Plain Python dict representation of the DockSpec

    Examples:
        >>> spec = DockSpec(...)
        >>> data = to_dict(spec)
        >>> data["agent"]["name"]
        'invoice-copilot'

        >>> # Include None values
        >>> data = to_dict(spec, exclude_none=False)
    """
    return spec.model_dump(exclude_none=exclude_none)


def to_yaml_string(spec: DockSpec, exclude_none: bool = True) -> str:
    """
    Serialize DockSpec to YAML string.

    NOTE: This returns a YAML string, NOT writing to a file.
    File writing is SDK's responsibility.

    Args:
        spec: DockSpec object to serialize
        exclude_none: If True, exclude fields with None values (default: True)

    Returns:
        YAML string representation of the DockSpec

    Raises:
        ImportError: If pyyaml is not installed

    Examples:
        >>> spec = DockSpec(...)
        >>> yaml_str = to_yaml_string(spec)
        >>> print(yaml_str)
        version: '1.0'
        agent:
          name: invoice-copilot
          entrypoint: app.main:build_graph
          framework: langgraph
        ...

        >>> # SDK would then write to file:
        >>> # with open("Dockfile.yaml", "w") as f:
        >>> #     f.write(yaml_str)
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for YAML serialization. Install with: pip install pyyaml"
        )

    data = to_dict(spec, exclude_none=exclude_none)

    # Use safe_dump with nice formatting
    return yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


def from_dict(data: Dict[str, Any]) -> DockSpec:
    """
    Create DockSpec from dictionary.

    This is a convenience wrapper around DockSpec.model_validate().
    It's provided for API consistency with to_dict().

    Args:
        data: Dictionary containing Dockfile configuration

    Returns:
        Validated DockSpec object

    Raises:
        ValidationError: If data doesn't match schema

    Examples:
        >>> data = {
        ...     "version": "1.0",
        ...     "agent": {
        ...         "name": "test-agent",
        ...         "entrypoint": "app.main:build",
        ...         "framework": "langgraph"
        ...     },
        ...     "io_schema": {},
        ...     "expose": {"port": 8080}
        ... }
        >>> spec = from_dict(data)
        >>> spec.agent.name
        'test-agent'
    """
    return DockSpec.model_validate(data)
