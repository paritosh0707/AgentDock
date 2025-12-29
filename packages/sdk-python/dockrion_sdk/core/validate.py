"""
Validation Module
=================

Provides comprehensive Dockfile validation:
- Schema validation
- Entrypoint/handler format validation
- Configuration warnings
"""

from typing import Any, Dict, List, Optional

from dockrion_common.errors import ValidationError
from dockrion_common.validation import validate_entrypoint
from dockrion_schema.dockfile_v1 import DockSpec

from .loader import load_dockspec


def validate_dockspec(path: str) -> Dict[str, Any]:
    """Validate a Dockfile and return detailed results.

    This function performs comprehensive validation including:
    - File existence check
    - YAML syntax validation
    - Schema validation (structure, types, required fields)
    - Entrypoint format validation
    - Environment variable expansion

    Args:
        path: Path to the Dockfile to validate

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "spec": DockSpec (if valid, None otherwise),
            "message": str (summary message)
        }

    Example:
        >>> result = validate_dockspec("Dockfile.yaml")
        >>> if result["valid"]:
        ...     print(f"✅ Valid: {result['message']}")
        ... else:
        ...     print(f"❌ Invalid: {', '.join(result['errors'])}")
    """
    errors: List[str] = []
    warnings: List[str] = []
    spec: Optional[DockSpec] = None

    # Try to load and validate the Dockfile
    try:
        spec = load_dockspec(path)
    except ValidationError as e:
        errors.append(str(e))
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "spec": None,
            "message": "Dockfile validation failed",
        }
    except Exception as e:
        errors.append(f"Unexpected error during validation: {str(e)}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "spec": None,
            "message": "Unexpected validation error",
        }

    # Additional validation checks
    # Check entrypoint format (only if entrypoint mode is used)
    if spec.agent.entrypoint:
        try:
            validate_entrypoint(spec.agent.entrypoint)
        except ValidationError as e:
            errors.append(f"Invalid entrypoint format: {str(e)}")

    # Validate handler format if handler mode is used
    if spec.agent.handler:
        try:
            from dockrion_common.validation import validate_handler

            validate_handler(spec.agent.handler)
        except ValidationError as e:
            errors.append(f"Invalid handler format: {str(e)}")

    # Check for potential issues (warnings)
    if spec.arguments and isinstance(spec.arguments, dict):
        timeout_sec = spec.arguments.get("timeout_sec")
        if timeout_sec is not None:
            if timeout_sec > 300:
                warnings.append(
                    f"Very high timeout ({timeout_sec}s). "
                    "Consider reducing for better user experience."
                )
            elif timeout_sec < 5:
                warnings.append(
                    f"Very low timeout ({timeout_sec}s). "
                    "Agent may not have enough time to complete."
                )

    # If we have errors, mark as invalid
    if errors:
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "spec": None,
            "message": f"Dockfile has {len(errors)} error(s)",
        }

    # Success!
    message = f"Dockfile is valid. Agent: {spec.agent.name}, Framework: {spec.agent.framework}"
    if warnings:
        message += f" ({len(warnings)} warning(s))"

    return {"valid": True, "errors": [], "warnings": warnings, "spec": spec, "message": message}


# Legacy function for backward compatibility
def validate(path: str) -> dict:
    """Legacy validation function (deprecated).

    Use validate_dockspec() instead for detailed validation results.

    Args:
        path: Path to the Dockfile

    Returns:
        {"valid": True} if valid, raises exception otherwise
    """
    result = validate_dockspec(path)
    if not result["valid"]:
        raise ValidationError(result["errors"][0] if result["errors"] else "Validation failed")
    return {"valid": True}


__all__ = [
    "validate_dockspec",
    "validate",
]
