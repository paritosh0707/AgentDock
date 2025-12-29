"""
Basic tests for dockrion-common package

This file contains smoke tests to verify the package implementation works.
More comprehensive tests should be added as the package is used.
"""

import pytest

from dockrion_common import (
    PERMISSIONS,
    # Constants
    SUPPORTED_FRAMEWORKS,
    AuthError,
    # Errors
    ErrorResponse,
    ValidationError,
    # Auth
    generate_api_key,
    hash_api_key,
    parse_rate_limit,
    validate_agent_name,
    validate_api_key,
    # Validation
    validate_entrypoint,
)


class TestErrors:
    """Test error classes"""

    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Test error")
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Test error"
        # str(error) returns the message
        assert "Test error" in str(error)

    def test_auth_error(self):
        """Test AuthError"""
        error = AuthError("Auth failed")
        assert error.code == "AUTH_ERROR"
        assert error.message == "Auth failed"

    def test_error_to_dict(self):
        """Test error serialization"""
        error = ValidationError("Test")
        error_dict = error.to_dict()
        assert error_dict["error"] == "ValidationError"
        assert error_dict["code"] == "VALIDATION_ERROR"
        assert error_dict["message"] == "Test"


class TestConstants:
    """Test constants"""

    def test_supported_frameworks(self):
        """Test SUPPORTED_FRAMEWORKS"""
        assert "langgraph" in SUPPORTED_FRAMEWORKS
        assert "langchain" in SUPPORTED_FRAMEWORKS

    def test_permissions(self):
        """Test PERMISSIONS"""
        assert "deploy" in PERMISSIONS
        assert "invoke" in PERMISSIONS


class TestValidation:
    """Test validation functions"""

    def test_validate_entrypoint_valid(self):
        """Test valid entrypoint"""
        module, func = validate_entrypoint("app.main:build_graph")
        assert module == "app.main"
        assert func == "build_graph"

    def test_validate_entrypoint_invalid(self):
        """Test invalid entrypoint"""
        with pytest.raises(ValidationError):
            validate_entrypoint("missing_colon")

    def test_validate_agent_name_valid(self):
        """Test valid agent name"""
        validate_agent_name("invoice-copilot")  # Should not raise
        validate_agent_name("my-agent-v2")  # Should not raise

    def test_validate_agent_name_invalid(self):
        """Test invalid agent name"""
        with pytest.raises(ValidationError):
            validate_agent_name("Invalid_Name")  # Uppercase/underscore

    def test_parse_rate_limit(self):
        """Test rate limit parsing"""
        count, seconds = parse_rate_limit("1000/m")
        assert count == 1000
        assert seconds == 60

        count, seconds = parse_rate_limit("100/s")
        assert count == 100
        assert seconds == 1


class TestAuth:
    """Test auth utilities"""

    def test_generate_api_key(self):
        """Test API key generation"""
        key = generate_api_key()
        assert key.startswith("agd_")
        assert len(key) > 10

    def test_hash_api_key(self):
        """Test API key hashing"""
        key = "agd_test123"
        hashed = hash_api_key(key)
        assert len(hashed) == 64  # SHA-256 hex digest
        assert hashed != key

    def test_validate_api_key_valid(self):
        """Test valid API key"""
        validate_api_key("test_key", "test_key")  # Should not raise

    def test_validate_api_key_invalid(self):
        """Test invalid API key"""
        with pytest.raises(AuthError):
            validate_api_key("wrong_key", "correct_key")

    def test_validate_api_key_missing(self):
        """Test missing API key"""
        with pytest.raises(AuthError):
            validate_api_key(None, "required_key")


class TestHTTPModels:
    """Test HTTP response models"""

    def test_error_response_creation(self):
        """Test ErrorResponse model creation"""
        response = ErrorResponse(error="Invalid input", code="VALIDATION_ERROR")
        assert response.success is False
        assert response.error == "Invalid input"
        assert response.code == "VALIDATION_ERROR"

    def test_error_response_model_dump(self):
        """Test ErrorResponse serialization"""
        response = ErrorResponse(error="Something went wrong", code="INTERNAL_ERROR")
        data = response.model_dump()
        assert data["success"] is False
        assert data["error"] == "Something went wrong"
        assert data["code"] == "INTERNAL_ERROR"


def test_package_imports():
    """Test that all expected exports are available"""
    from dockrion_common import __all__, __version__

    assert __version__ == "0.1.0"
    assert isinstance(__all__, list)
    assert len(__all__) > 0
