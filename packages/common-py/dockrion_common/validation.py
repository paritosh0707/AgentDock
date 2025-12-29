"""
dockrion Validation Utilities

This module provides reusable validation functions used across dockrion packages.
All validation functions raise ValidationError on invalid input.

Usage:
    from dockrion_common.validation import validate_entrypoint, validate_agent_name
    
    module, func = validate_entrypoint("app.main:build_graph")
    validate_agent_name("my-agent")
"""

import re
from typing import Tuple

from .errors import ValidationError
from .constants import Patterns


def validate_entrypoint(entrypoint: str) -> Tuple[str, str]:
    """
    Validate and parse entrypoint format: 'module.path:callable'.
    
    Args:
        entrypoint: Entrypoint string to validate
        
    Returns:
        Tuple of (module_path, callable_name)
        
    Raises:
        ValidationError: If entrypoint format is invalid
        
    Examples:
        >>> validate_entrypoint("app.main:build_graph")
        ('app.main', 'build_graph')
        
        >>> validate_entrypoint("my_module:create_agent")
        ('my_module', 'create_agent')
    """
    if not entrypoint:
        raise ValidationError("Entrypoint cannot be empty")
    
    if ":" not in entrypoint:
        raise ValidationError(
            "Entrypoint must be in format 'module:callable'. "
            f"Got: '{entrypoint}'"
        )
    
    parts = entrypoint.split(":")
    if len(parts) != 2:
        raise ValidationError(
            "Entrypoint must have exactly one ':' separator. "
            f"Got: '{entrypoint}'"
        )
    
    module_path, callable_name = parts
    
    if not module_path or not callable_name:
        raise ValidationError(
            "Both module and callable must be non-empty. "
            f"Got: '{entrypoint}'"
        )
    
    # Validate format using pattern
    if not re.match(Patterns.ENTRYPOINT, entrypoint):
        raise ValidationError(
            "Entrypoint contains invalid characters. "
            "Use only alphanumeric, dots (.), and underscores (_). "
            f"Got: '{entrypoint}'"
        )
    
    return module_path.strip(), callable_name.strip()


def validate_handler(handler: str) -> Tuple[str, str]:
    """
    Validate and parse handler format: 'module.path:callable'.
    
    Handlers are direct callable functions (not factories that return agents).
    The format is identical to entrypoint, but semantic meaning differs:
    - entrypoint: factory function that returns an agent with .invoke() method
    - handler: direct callable function that processes requests
    
    Args:
        handler: Handler string to validate
        
    Returns:
        Tuple of (module_path, callable_name)
        
    Raises:
        ValidationError: If handler format is invalid
        
    Examples:
        >>> validate_handler("app.service:process_request")
        ('app.service', 'process_request')
        
        >>> validate_handler("mymodule:handle_invoice")
        ('mymodule', 'handle_invoice')
    """
    if not handler:
        raise ValidationError("Handler cannot be empty")
    
    if ":" not in handler:
        raise ValidationError(
            "Handler must be in format 'module:callable'. "
            f"Got: '{handler}'"
        )
    
    parts = handler.split(":")
    if len(parts) != 2:
        raise ValidationError(
            "Handler must have exactly one ':' separator. "
            f"Got: '{handler}'"
        )
    
    module_path, callable_name = parts
    
    if not module_path or not callable_name:
        raise ValidationError(
            "Both module and callable must be non-empty. "
            f"Got: '{handler}'"
        )
    
    # Validate format using pattern
    if not re.match(Patterns.HANDLER, handler):
        raise ValidationError(
            "Handler contains invalid characters. "
            "Use only alphanumeric, dots (.), and underscores (_). "
            f"Got: '{handler}'"
        )
    
    return module_path.strip(), callable_name.strip()


def validate_agent_name(name: str) -> None:
    """
    Validate agent name format (lowercase, alphanumeric, hyphens only).
    
    Args:
        name: Agent name to validate
        
    Raises:
        ValidationError: If name format is invalid
        
    Examples:
        >>> validate_agent_name("my-agent")  # Valid
        >>> validate_agent_name("invoice-copilot-v2")  # Valid
        >>> validate_agent_name("My-Agent")  # Raises ValidationError (uppercase)
    """
    if not name:
        raise ValidationError("Agent name cannot be empty")
    
    if not re.match(Patterns.AGENT_NAME, name):
        raise ValidationError(
            "Agent name must be lowercase alphanumeric with hyphens only. "
            f"Got: '{name}'"
        )
    
    if len(name) > 63:
        raise ValidationError(
            f"Agent name must be 63 characters or less. Got {len(name)} characters."
        )
    
    if name.startswith("-") or name.endswith("-"):
        raise ValidationError(
            f"Agent name cannot start or end with a hyphen. Got: '{name}'"
        )


def parse_rate_limit(limit_str: str) -> Tuple[int, int]:
    """
    Parse rate limit string to (count, seconds).
    
    Supported formats:
    - '100/s' -> 100 per second
    - '1000/m' -> 1000 per minute
    - '5000/h' -> 5000 per hour
    - '10000/d' -> 10000 per day
    
    Args:
        limit_str: Rate limit string to parse
        
    Returns:
        Tuple of (count, seconds) where seconds is the time window
        
    Raises:
        ValidationError: If format is invalid
        
    Examples:
        >>> parse_rate_limit("100/s")
        (100, 1)
        
        >>> parse_rate_limit("1000/m")
        (1000, 60)
        
        >>> parse_rate_limit("5000/h")
        (5000, 3600)
    """
    if not limit_str:
        raise ValidationError("Rate limit cannot be empty")
    
    match = re.match(Patterns.RATE_LIMIT, limit_str)
    if not match:
        raise ValidationError(
            "Rate limit must be in format 'number/unit' where unit is s, m, h, or d. "
            f"Examples: '100/s', '1000/m', '5000/h'. Got: '{limit_str}'"
        )
    
    count = int(match.group(1))
    unit = match.group(2)
    
    unit_to_seconds = {
        's': 1,        # second
        'm': 60,       # minute
        'h': 3600,     # hour
        'd': 86400,    # day
    }
    
    seconds = unit_to_seconds[unit]
    
    if count <= 0:
        raise ValidationError(
            f"Rate limit count must be positive. Got: {count}"
        )
    
    return count, seconds


def validate_url(url: str) -> None:
    """
    Validate URL format.
    
    Args:
        url: URL string to validate
        
    Raises:
        ValidationError: If URL format is invalid
        
    Examples:
        >>> validate_url("http://localhost:8080")  # Valid
        >>> validate_url("https://api.example.com/v1")  # Valid
        >>> validate_url("not a url")  # Raises ValidationError
    """
    if not url:
        raise ValidationError("URL cannot be empty")
    
    # Basic URL validation
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(url_pattern, url, re.IGNORECASE):
        raise ValidationError(
            f"Invalid URL format. Must start with http:// or https://. Got: '{url}'"
        )


def sanitize_input(text: str, max_length: int | None = None) -> str:
    """
    Sanitize user input by trimming whitespace and enforcing length limits.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (optional)
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If text exceeds max_length
        
    Examples:
        >>> sanitize_input("  hello  ")
        'hello'
        
        >>> sanitize_input("test", max_length=3)
        ValidationError: Input exceeds maximum length of 3 characters
    """
    if not isinstance(text, str):
        raise ValidationError(f"Input must be a string. Got: {type(text).__name__}")
    
    sanitized = text.strip()
    
    if max_length is not None and len(sanitized) > max_length:
        raise ValidationError(
            f"Input exceeds maximum length of {max_length} characters. "
            f"Got: {len(sanitized)} characters."
        )
    
    return sanitized


def validate_port(port: int) -> None:
    """
    Validate port number is in valid range (1-65535).
    
    Args:
        port: Port number to validate
        
    Raises:
        ValidationError: If port is out of range
        
    Examples:
        >>> validate_port(8080)  # Valid
        >>> validate_port(0)  # Raises ValidationError
        >>> validate_port(70000)  # Raises ValidationError
    """
    if not isinstance(port, int):
        raise ValidationError(f"Port must be an integer. Got: {type(port).__name__}")
    
    if port < 1 or port > 65535:
        raise ValidationError(
            f"Port must be between 1 and 65535. Got: {port}"
        )


def validate_version(version: str) -> None:
    """
    Validate semantic version format (e.g., '1.0', '1.2.3').
    
    Args:
        version: Version string to validate
        
    Raises:
        ValidationError: If version format is invalid
        
    Examples:
        >>> validate_version("1.0")  # Valid
        >>> validate_version("1.2.3")  # Valid
        >>> validate_version("v1.0")  # Raises ValidationError
    """
    if not version:
        raise ValidationError("Version cannot be empty")
    
    version_pattern = r'^\d+\.\d+(\.\d+)?$'
    if not re.match(version_pattern, version):
        raise ValidationError(
            "Version must be in format 'major.minor' or 'major.minor.patch'. "
            f"Examples: '1.0', '1.2.3'. Got: '{version}'"
        )

