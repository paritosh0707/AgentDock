"""
Schema Utilities

Utilities for creating Pydantic models from JSON Schema definitions.
Enables automatic FastAPI request validation and OpenAPI schema generation.
"""

from typing import Any, Optional, Type

from pydantic import BaseModel, Field, create_model


def create_pydantic_model_from_schema(
    schema_name: str, json_schema: Optional[Any]
) -> Type[BaseModel]:
    """
    Create a Pydantic model from JSON Schema definition.

    This enables automatic FastAPI request validation and OpenAPI schema generation.

    Args:
        schema_name: Name for the generated model
        json_schema: JSON Schema definition (IOSubSchema)

    Returns:
        Pydantic BaseModel class

    Example:
        >>> model = create_pydantic_model_from_schema(
        ...     "InvoiceInput",
        ...     io_schema.input
        ... )
        >>> instance = model(document_text="...", currency_hint="USD")
    """
    if not json_schema or not hasattr(json_schema, "properties"):
        # Return a generic dict model if no schema
        return create_model(
            schema_name,
            __base__=BaseModel,
        )

    # Map JSON Schema types to Python types
    type_mapping: dict[str, type] = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    # Build field definitions
    field_definitions: dict[str, Any] = {}
    properties = json_schema.properties if hasattr(json_schema, "properties") else {}
    required_fields = json_schema.required if hasattr(json_schema, "required") else []

    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue

        # Get type
        field_type_str = field_schema.get("type", "string")
        field_type = type_mapping.get(field_type_str, Any)

        # Get description
        description = field_schema.get("description", "")

        # Determine if required
        is_required = field_name in required_fields

        # Create Field with metadata
        if is_required:
            field_definitions[field_name] = (field_type, Field(..., description=description))
        else:
            field_definitions[field_name] = (
                Optional[field_type],
                Field(None, description=description),
            )

    # Create the model
    return create_model(schema_name, __base__=BaseModel, **field_definitions)
