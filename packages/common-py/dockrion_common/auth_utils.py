"""
dockrion Authentication Utilities

This module provides authentication and authorization utilities for API key management,
token validation, and permission checking.

Usage:
    from dockrion_common.auth_utils import generate_api_key, validate_api_key
    
    new_key = generate_api_key()
    validate_api_key(request.headers.get("X-API-Key"), expected_key)
"""

import secrets
import hashlib
from typing import List

from .errors import AuthError


def generate_api_key(prefix: str = "agd") -> str:
    """
    Generate a secure API key.
    
    Format: {prefix}_{random_32_chars}
    Uses cryptographically secure random generation.
    
    Args:
        prefix: Prefix for the API key (default: "agd")
        
    Returns:
        Generated API key string
        
    Examples:
        >>> key = generate_api_key()
        >>> key.startswith("agd_")
        True
        >>> len(key)
        36  # "agd_" (4) + 32 random characters
        
        >>> key = generate_api_key(prefix="test")
        >>> key.startswith("test_")
        True
    """
    random_part = secrets.token_urlsafe(24)  # Generates ~32 chars
    return f"{prefix}_{random_part}"


def hash_api_key(key: str) -> str:
    """
    Hash API key for secure storage (one-way hash using SHA-256).
    
    Never store API keys in plain text. Always hash them before storage
    and compare hashed values during validation.
    
    Args:
        key: API key to hash
        
    Returns:
        Hex digest of the hashed key
        
    Examples:
        >>> hash_api_key("agd_test123")
        'a1b2c3d4e5f6...'  # 64-character hex string
    """
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def validate_api_key(header_value: str | None, expected: str | None) -> None:
    """
    Validate API key from request header.
    
    Args:
        header_value: API key from request header (e.g., X-API-Key)
        expected: Expected API key value
        
    Raises:
        AuthError: If API key is invalid or missing
        
    Examples:
        >>> validate_api_key("agd_valid_key", "agd_valid_key")  # Success
        
        >>> validate_api_key(None, "agd_valid_key")
        AuthError: API key required
        
        >>> validate_api_key("wrong_key", "agd_valid_key")
        AuthError: Invalid API key
    """
    if not expected:
        # No API key required
        return
    
    if not header_value:
        raise AuthError("API key required")
    
    if header_value != expected:
        raise AuthError("Invalid API key")


def extract_bearer_token(authorization: str | None) -> str | None:
    """
    Extract token from 'Bearer <token>' authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Extracted token or None if header is invalid/missing
        
    Examples:
        >>> extract_bearer_token("Bearer abc123")
        'abc123'
        
        >>> extract_bearer_token("Basic xyz")
        None
        
        >>> extract_bearer_token(None)
        None
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2:
        return None
    
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    
    return token


def check_permission(user_permissions: List[str], required: str) -> bool:
    """
    Check if user has the required permission.
    
    Args:
        user_permissions: List of permissions the user has
        required: Required permission to check
        
    Returns:
        True if user has the required permission, False otherwise
        
    Examples:
        >>> check_permission(["deploy", "invoke"], "deploy")
        True
        
        >>> check_permission(["invoke"], "deploy")
        False
        
        >>> check_permission([], "deploy")
        False
    """
    return required in user_permissions


def check_any_permission(user_permissions: List[str], required: List[str]) -> bool:
    """
    Check if user has any of the required permissions.
    
    Args:
        user_permissions: List of permissions the user has
        required: List of required permissions (user needs at least one)
        
    Returns:
        True if user has at least one required permission, False otherwise
        
    Examples:
        >>> check_any_permission(["invoke"], ["deploy", "invoke"])
        True
        
        >>> check_any_permission(["read_logs"], ["deploy", "invoke"])
        False
    """
    return any(perm in user_permissions for perm in required)


def check_all_permissions(user_permissions: List[str], required: List[str]) -> bool:
    """
    Check if user has all of the required permissions.
    
    Args:
        user_permissions: List of permissions the user has
        required: List of required permissions (user needs all)
        
    Returns:
        True if user has all required permissions, False otherwise
        
    Examples:
        >>> check_all_permissions(["deploy", "invoke", "read_logs"], ["deploy", "invoke"])
        True
        
        >>> check_all_permissions(["deploy"], ["deploy", "invoke"])
        False
    """
    return all(perm in user_permissions for perm in required)


def verify_api_key_format(key: str) -> bool:
    """
    Verify API key has correct format (prefix_randomchars).
    
    This is a basic format check, not authentication validation.
    
    Args:
        key: API key to check
        
    Returns:
        True if format is valid, False otherwise
        
    Examples:
        >>> verify_api_key_format("agd_abc123def456")
        True
        
        >>> verify_api_key_format("invalid")
        False
        
        >>> verify_api_key_format("agd_")
        False
    """
    if not key or "_" not in key:
        return False
    
    parts = key.split("_", 1)
    if len(parts) != 2:
        return False
    
    prefix, random_part = parts
    
    # Prefix should be alphanumeric
    if not prefix.isalnum():
        return False
    
    # Random part should be at least 16 characters
    if len(random_part) < 16:
        return False
    
    return True
