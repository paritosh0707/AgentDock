"""
dockrion JSON Schema Generation

This module provides utilities for generating JSON Schema v7 from DockSpec models.

Use Cases:
- IDE autocomplete while writing Dockfiles (VS Code, PyCharm)
- Client-side validation before sending to API
- OpenAPI documentation generation
- Schema visualization tools

Usage:
    from dockrion_schema import generate_json_schema
    
    # Get JSON Schema as dict
    schema = generate_json_schema()
    
    # Optionally write to file for editor plugins
    # (This is the ONLY file I/O in schema package, for tooling support)
    write_json_schema("dockfile_v1_schema.json")
"""

import json
from typing import Dict, Any

from .dockfile_v1 import DockSpec


def generate_json_schema() -> Dict[str, Any]:
    """
    Generate JSON Schema v7 for Dockfile v1.0 specification.
    
    This generates a JSON Schema that can be used by:
    - Code editors for autocomplete and validation
    - API clients for request validation
    - Documentation tools
    
    Returns:
        JSON Schema dictionary (version 7)
        
    Examples:
        >>> schema = generate_json_schema()
        >>> schema["$schema"]
        'https://json-schema.org/draft-07/schema#'
        
        >>> schema["properties"]["agent"]["required"]
        ['name', 'entrypoint', 'framework']
    """
    return DockSpec.model_json_schema()


def write_json_schema(output_path: str = "dockfile_v1_schema.json") -> None:
    """
    Write JSON Schema to file for editor plugins and tools.
    
    NOTE: This is the ONLY file I/O operation in the schema package.
    It's provided for developer tooling support (VS Code extensions, etc.).
    
    The schema file can be referenced in IDE settings or YAML frontmatter:
        # yaml-language-server: $schema=./dockfile_v1_schema.json
    
    Args:
        output_path: Path where JSON Schema file will be written
                    (default: "dockfile_v1_schema.json")
        
    Raises:
        IOError: If file cannot be written
        
    Examples:
        >>> # Generate schema file for IDE support
        >>> write_json_schema("dockfile_v1_schema.json")
        
        >>> # Then reference in Dockfile.yaml:
        >>> # yaml-language-server: $schema=./dockfile_v1_schema.json
        >>> # version: "1.0"
        >>> # ...
    """
    schema = generate_json_schema()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add trailing newline
    
    print(f"✅ JSON Schema written to: {output_path}")
    print(f"📝 Add this to your Dockfile.yaml for IDE support:")
    print(f"   # yaml-language-server: $schema=./{output_path}")


def get_schema_version() -> str:
    """
    Get the Dockfile schema version.
    
    Returns:
        Version string (e.g., "1.0")
    """
    return "1.0"

