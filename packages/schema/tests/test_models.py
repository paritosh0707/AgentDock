"""
Comprehensive tests for Dockfile schema models.

Tests cover:
- Valid configurations (minimal and full)
- Invalid configurations (missing fields, wrong types)
- Field validators (entrypoint, port, framework, etc.)
- Model validators (cross-field validation)
- Edge cases (empty lists, None values, boundaries)
"""

import pytest
from dockrion_schema import (
    DockSpec,
    AgentConfig,
    IOSchema,
    IOSubSchema,
    ExposeConfig,
    Metadata,
    ModelConfig,
    Policies,
    ToolPolicy,
    SafetyPolicy,
    AuthConfig,
    RoleConfig,
    ApiKeysConfig,
    Observability,
    ValidationError,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def minimal_valid_dockfile():
    """Minimal valid Dockfile configuration"""
    return {
        "version": "1.0",
        "agent": {
            "name": "test-agent",
            "entrypoint": "app.main:build_graph",
            "framework": "langgraph"
        },
        "io_schema": {},
        "expose": {
            "port": 8080
        }
    }


@pytest.fixture
def full_valid_dockfile():
    """Full Dockfile with all optional fields"""
    return {
        "version": "1.0",
        "agent": {
            "name": "invoice-copilot",
            "description": "Extracts data from invoices",
            "entrypoint": "examples.invoice_copilot.app.graph:build_graph",
            "framework": "langgraph"
        },
        "model": {
            "provider": "openai",
            "name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1500
        },
        "io_schema": {
            "input": {
                "type": "object",
                "properties": {
                    "document_text": {"type": "string"},
                    "currency_hint": {"type": "string"}
                },
                "required": ["document_text"]
            },
            "output": {
                "type": "object",
                "properties": {
                    "vendor": {"type": "string"},
                    "total": {"type": "number"}
                }
            }
        },
        "arguments": {
            "max_retries": 3,
            "timeout": 30
        },
        "policies": {
            "tools": {
                "allowed": ["extract_invoice", "summarize"],
                "deny_by_default": True
            },
            "safety": {
                "redact_patterns": [r"\b\d{16}\b"],
                "max_output_chars": 5000,
                "block_prompt_injection": True
            }
        },
        "auth": {
            "mode": "api_key",
            "api_keys": {
                "enabled": True,
                "rotation_days": 30
            },
            "roles": [
                {
                    "name": "admin",
                    "permissions": ["deploy", "invoke", "view_metrics"]
                }
            ],
            "rate_limits": {
                "admin": "1000/m",
                "viewer": "60/m"
            }
        },
        "observability": {
            "tracing": True,
            "log_level": "info",
            "metrics": {
                "latency": True,
                "tokens": True,
                "cost": True
            }
        },
        "expose": {
            "rest": True,
            "streaming": "sse",
            "port": 8080,
            "host": "0.0.0.0",
            "cors": {
                "origins": ["http://localhost:3000"],
                "methods": ["GET", "POST"]
            }
        },
        "metadata": {
            "maintainer": "alice@example.com",
            "version": "1.0.0",
            "tags": ["invoice", "extraction", "production"]
        }
    }


# =============================================================================
# DOCKSPEC VALIDATION TESTS
# =============================================================================

class TestDockSpec:
    """Tests for DockSpec root model"""
    
    def test_minimal_valid_dockfile(self, minimal_valid_dockfile):
        """Test minimal valid configuration"""
        spec = DockSpec.model_validate(minimal_valid_dockfile)
        assert spec.version == "1.0"
        assert spec.agent.name == "test-agent"
        assert spec.agent.entrypoint == "app.main:build_graph"
        assert spec.agent.framework == "langgraph"
        assert spec.expose.port == 8080
    
    def test_full_valid_dockfile(self, full_valid_dockfile):
        """Test full configuration with all fields"""
        spec = DockSpec.model_validate(full_valid_dockfile)
        assert spec.version == "1.0"
        assert spec.agent.name == "invoice-copilot"
        assert spec.model.provider == "openai"
        assert spec.policies.tools.allowed == ["extract_invoice", "summarize"]
        assert spec.auth.mode == "api_key"
        assert spec.observability.log_level == "info"
        assert spec.metadata.maintainer == "alice@example.com"
    
    def test_missing_required_field_version(self):
        """Test missing version field"""
        data = {
            "agent": {
                "name": "test",
                "entrypoint": "app:main",
                "framework": "langgraph"
            },
            "io_schema": {},
            "expose": {"port": 8080}
        }
        with pytest.raises(Exception):  # Pydantic ValidationError
            DockSpec.model_validate(data)
    
    def test_missing_required_field_agent(self):
        """Test missing agent field"""
        data = {
            "version": "1.0",
            "io_schema": {},
            "expose": {"port": 8080}
        }
        with pytest.raises(Exception):  # Pydantic ValidationError
            DockSpec.model_validate(data)
    
    def test_unsupported_version(self):
        """Test unsupported version"""
        data = {
            "version": "2.0",  # Not supported yet
            "agent": {
                "name": "test",
                "entrypoint": "app:main",
                "framework": "langgraph"
            },
            "io_schema": {},
            "expose": {"port": 8080}
        }
        # Pydantic will catch this at the Literal level before our validator runs
        with pytest.raises(Exception) as exc_info:
            DockSpec.model_validate(data)
        assert "literal_error" in str(exc_info.value) or "Input should be '1.0'" in str(exc_info.value)
    
    def test_extra_fields_allowed(self, minimal_valid_dockfile):
        """Test that unknown fields are accepted (extensibility)"""
        minimal_valid_dockfile["future_field"] = "future_value"
        minimal_valid_dockfile["another_section"] = {"key": "value"}
        
        # Should not raise - extra fields are allowed
        spec = DockSpec.model_validate(minimal_valid_dockfile)
        assert spec.version == "1.0"


# =============================================================================
# AGENT CONFIG VALIDATION TESTS
# =============================================================================

class TestAgentConfig:
    """Tests for AgentConfig model"""
    
    def test_valid_agent_config(self):
        """Test valid agent configuration"""
        data = {
            "name": "test-agent",
            "entrypoint": "app.main:build_graph",
            "framework": "langgraph"
        }
        agent = AgentConfig.model_validate(data)
        assert agent.name == "test-agent"
        assert agent.entrypoint == "app.main:build_graph"
        assert agent.framework == "langgraph"
    
    def test_agent_name_validation_valid(self):
        """Test valid agent names"""
        valid_names = ["test-agent", "invoice-copilot-v2", "my-agent-123"]
        for name in valid_names:
            data = {
                "name": name,
                "entrypoint": "app:main",
                "framework": "langgraph"
            }
            agent = AgentConfig.model_validate(data)
            assert agent.name == name
    
    def test_agent_name_validation_invalid_uppercase(self):
        """Test agent name with uppercase (invalid)"""
        data = {
            "name": "Test-Agent",  # Uppercase not allowed
            "entrypoint": "app:main",
            "framework": "langgraph"
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig.model_validate(data)
        assert "lowercase" in str(exc_info.value).lower()
    
    def test_agent_name_validation_invalid_underscore(self):
        """Test agent name with underscore (invalid)"""
        data = {
            "name": "test_agent",  # Underscore not allowed
            "entrypoint": "app:main",
            "framework": "langgraph"
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig.model_validate(data)
        assert "alphanumeric" in str(exc_info.value).lower()
    
    def test_entrypoint_validation_valid(self):
        """Test valid entrypoint formats"""
        valid_entrypoints = [
            "app.main:build_graph",
            "my_module:create_agent",
            "package.subpackage.module:function",
        ]
        for entrypoint in valid_entrypoints:
            data = {
                "name": "test",
                "entrypoint": entrypoint,
                "framework": "langgraph"
            }
            agent = AgentConfig.model_validate(data)
            assert agent.entrypoint == entrypoint
    
    def test_entrypoint_validation_missing_colon(self):
        """Test entrypoint without colon (invalid)"""
        data = {
            "name": "test",
            "entrypoint": "missing_colon",  # No ':'
            "framework": "langgraph"
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig.model_validate(data)
        assert ":" in str(exc_info.value)
    
    def test_entrypoint_validation_injection_attempt(self):
        """Test entrypoint injection prevention"""
        # The second one has invalid characters (slashes in path traversal)
        data = {
            "name": "test",
            "entrypoint": "../../../etc/passwd:read",  # Path traversal attempt
            "framework": "langgraph"
        }
        # Validation should catch invalid characters (dots and slashes at start)
        with pytest.raises(ValidationError):
            AgentConfig.model_validate(data)
        
        # Note: "os.system:eval" is technically valid format (module.path:callable)
        # but runtime import would fail - that's intentional
    
    def test_framework_validation_valid(self):
        """Test valid frameworks"""
        for framework in ["langgraph", "langchain"]:
            data = {
                "name": "test",
                "entrypoint": "app:main",
                "framework": framework
            }
            agent = AgentConfig.model_validate(data)
            assert agent.framework == framework
    
    def test_framework_validation_invalid(self):
        """Test unsupported framework"""
        data = {
            "name": "test",
            "entrypoint": "app:main",
            "framework": "autogen"  # Not supported yet
        }
        # Pydantic Literal validation catches this before our validator
        with pytest.raises(Exception) as exc_info:
            AgentConfig.model_validate(data)
        assert "literal_error" in str(exc_info.value) or "langgraph" in str(exc_info.value)


# =============================================================================
# MODEL CONFIG VALIDATION TESTS
# =============================================================================

class TestModelConfig:
    """Tests for ModelConfig model"""
    
    def test_valid_model_config(self):
        """Test valid model configuration"""
        data = {
            "provider": "openai",
            "name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1500
        }
        model = ModelConfig.model_validate(data)
        assert model.provider == "openai"
        assert model.name == "gpt-4o-mini"
        assert model.temperature == 0.7
        assert model.max_tokens == 1500
    
    def test_provider_validation_valid(self):
        """Test valid providers"""
        providers = ["openai", "azure", "anthropic", "google", "ollama", "custom"]
        for provider in providers:
            data = {"provider": provider, "name": "test-model"}
            model = ModelConfig.model_validate(data)
            assert model.provider == provider
    
    def test_provider_validation_invalid(self):
        """Test unsupported provider"""
        data = {"provider": "unsupported", "name": "test"}
        # Pydantic Literal validation catches this before our validator
        with pytest.raises(Exception) as exc_info:
            ModelConfig.model_validate(data)
        assert "literal_error" in str(exc_info.value) or "openai" in str(exc_info.value)
    
    def test_temperature_range_validation(self):
        """Test temperature range validation"""
        # Valid temperatures
        for temp in [0, 0.5, 1.0, 1.5, 2.0]:
            data = {"provider": "openai", "name": "gpt-4", "temperature": temp}
            model = ModelConfig.model_validate(data)
            assert model.temperature == temp
        
        # Invalid temperatures
        for temp in [-0.1, 2.1, 3.0]:
            data = {"provider": "openai", "name": "gpt-4", "temperature": temp}
            with pytest.raises(ValidationError):
                ModelConfig.model_validate(data)
    
    def test_max_tokens_validation(self):
        """Test max_tokens validation"""
        # Valid
        data = {"provider": "openai", "name": "gpt-4", "max_tokens": 1000}
        model = ModelConfig.model_validate(data)
        assert model.max_tokens == 1000
        
        # Invalid (non-positive)
        for tokens in [0, -1, -100]:
            data = {"provider": "openai", "name": "gpt-4", "max_tokens": tokens}
            with pytest.raises(ValidationError):
                ModelConfig.model_validate(data)


# =============================================================================
# EXPOSE CONFIG VALIDATION TESTS
# =============================================================================

class TestExposeConfig:
    """Tests for ExposeConfig model"""
    
    def test_valid_expose_config(self):
        """Test valid expose configuration"""
        data = {
            "rest": True,
            "streaming": "sse",
            "port": 8080,
            "host": "0.0.0.0"
        }
        expose = ExposeConfig.model_validate(data)
        assert expose.rest is True
        assert expose.streaming == "sse"
        assert expose.port == 8080
        assert expose.host == "0.0.0.0"
    
    def test_port_range_validation_valid(self):
        """Test valid port numbers"""
        for port in [1, 80, 8080, 65535]:
            data = {"port": port}
            expose = ExposeConfig.model_validate(data)
            assert expose.port == port
    
    def test_port_range_validation_invalid(self):
        """Test invalid port numbers"""
        for port in [0, -1, 65536, 70000]:
            data = {"port": port}
            with pytest.raises(ValidationError):
                ExposeConfig.model_validate(data)
    
    def test_streaming_mode_validation_valid(self):
        """Test valid streaming modes"""
        for mode in ["sse", "websocket", "none"]:
            data = {"port": 8080, "streaming": mode}
            expose = ExposeConfig.model_validate(data)
            assert expose.streaming == mode
    
    def test_streaming_mode_validation_invalid(self):
        """Test invalid streaming mode"""
        data = {"port": 8080, "streaming": "grpc"}  # Not supported
        # Pydantic Literal validation catches this before our validator
        with pytest.raises(Exception) as exc_info:
            ExposeConfig.model_validate(data)
        assert "literal_error" in str(exc_info.value) or "sse" in str(exc_info.value)
    
    def test_at_least_one_exposure_required_valid(self):
        """Test that at least one exposure method is enabled"""
        # Valid: REST enabled
        data = {"port": 8080, "rest": True, "streaming": "none"}
        expose = ExposeConfig.model_validate(data)
        assert expose.rest is True
        
        # Valid: Streaming enabled
        data = {"port": 8080, "rest": False, "streaming": "sse"}
        expose = ExposeConfig.model_validate(data)
        assert expose.streaming == "sse"
        
        # Valid: Both enabled
        data = {"port": 8080, "rest": True, "streaming": "sse"}
        expose = ExposeConfig.model_validate(data)
        assert expose.rest is True
    
    def test_at_least_one_exposure_required_invalid(self):
        """Test that validation fails when no exposure method is enabled"""
        data = {"port": 8080, "rest": False, "streaming": "none"}
        with pytest.raises(ValidationError) as exc_info:
            ExposeConfig.model_validate(data)
        assert "At least one exposure method" in str(exc_info.value)


# =============================================================================
# AUTH CONFIG VALIDATION TESTS
# =============================================================================

class TestAuthConfig:
    """Tests for AuthConfig model"""
    
    def test_valid_auth_config(self):
        """Test valid auth configuration"""
        data = {
            "mode": "api_key",
            "api_keys": {"enabled": True},
            "roles": [
                {"name": "admin", "permissions": ["deploy", "invoke"]}
            ],
            "rate_limits": {"admin": "1000/m"}
        }
        auth = AuthConfig.model_validate(data)
        assert auth.mode == "api_key"
        assert len(auth.roles) == 1
    
    def test_auth_mode_validation(self):
        """Test auth mode validation"""
        for mode in ["jwt", "api_key", "oauth2"]:
            data = {"mode": mode}
            auth = AuthConfig.model_validate(data)
            assert auth.mode == mode
        
        # Invalid mode
        data = {"mode": "ldap"}  # Not supported
        # Pydantic Literal validation catches this before our validator
        with pytest.raises(Exception):
            AuthConfig.model_validate(data)
    
    def test_role_permissions_validation(self):
        """Test role permissions validation"""
        # Valid permissions
        data = {
            "roles": [
                {"name": "admin", "permissions": ["deploy", "invoke", "view_metrics"]}
            ]
        }
        auth = AuthConfig.model_validate(data)
        assert len(auth.roles[0].permissions) == 3
        
        # Invalid permission
        data = {
            "roles": [
                {"name": "admin", "permissions": ["invalid_permission"]}
            ]
        }
        with pytest.raises(ValidationError) as exc_info:
            AuthConfig.model_validate(data)
        assert "Unknown permission" in str(exc_info.value)
    
    def test_rate_limit_format_validation(self):
        """Test rate limit format validation"""
        # Valid formats
        valid_limits = {
            "admin": "1000/m",
            "viewer": "60/s",
            "premium": "5000/h"
        }
        data = {"rate_limits": valid_limits}
        auth = AuthConfig.model_validate(data)
        assert auth.rate_limits == valid_limits
        
        # Invalid format
        data = {"rate_limits": {"admin": "invalid"}}
        with pytest.raises(ValidationError):
            AuthConfig.model_validate(data)


# =============================================================================
# POLICIES VALIDATION TESTS
# =============================================================================

class TestPolicies:
    """Tests for Policies model"""
    
    def test_valid_policies(self):
        """Test valid policies configuration"""
        data = {
            "tools": {
                "allowed": ["tool1", "tool2"],
                "deny_by_default": True
            },
            "safety": {
                "redact_patterns": [r"\d{16}"],
                "max_output_chars": 5000,
                "block_prompt_injection": True
            }
        }
        policies = Policies.model_validate(data)
        assert len(policies.tools.allowed) == 2
        assert policies.safety.max_output_chars == 5000
    
    def test_max_output_chars_validation(self):
        """Test max_output_chars validation"""
        # Valid
        data = {"safety": {"max_output_chars": 1000}}
        policies = Policies.model_validate(data)
        assert policies.safety.max_output_chars == 1000
        
        # Invalid (non-positive)
        for chars in [0, -1, -100]:
            data = {"safety": {"max_output_chars": chars}}
            with pytest.raises(ValidationError):
                Policies.model_validate(data)


# =============================================================================
# OBSERVABILITY VALIDATION TESTS
# =============================================================================

class TestObservability:
    """Tests for Observability model"""
    
    def test_valid_observability(self):
        """Test valid observability configuration"""
        data = {
            "tracing": True,
            "log_level": "info",
            "metrics": {"latency": True, "tokens": True}
        }
        obs = Observability.model_validate(data)
        assert obs.tracing is True
        assert obs.log_level == "info"
    
    def test_log_level_validation(self):
        """Test log level validation"""
        for level in ["debug", "info", "warn", "error"]:
            data = {"log_level": level}
            obs = Observability.model_validate(data)
            assert obs.log_level == level
        
        # Invalid level
        data = {"log_level": "trace"}  # Not supported
        # Pydantic Literal validation catches this before our validator
        with pytest.raises(Exception):
            Observability.model_validate(data)


# =============================================================================
# EDGE CASES AND SPECIAL TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_empty_optional_fields(self, minimal_valid_dockfile):
        """Test with empty optional fields"""
        minimal_valid_dockfile["metadata"] = {}
        minimal_valid_dockfile["arguments"] = {}
        
        spec = DockSpec.model_validate(minimal_valid_dockfile)
        assert spec.metadata is not None
        assert spec.arguments == {}
    
    def test_none_optional_fields(self, minimal_valid_dockfile):
        """Test with None for optional fields"""
        minimal_valid_dockfile["metadata"] = None
        minimal_valid_dockfile["model"] = None
        
        spec = DockSpec.model_validate(minimal_valid_dockfile)
        assert spec.metadata is None
        assert spec.model is None
    
    def test_empty_lists(self):
        """Test with empty lists"""
        data = {
            "metadata": {"tags": []},
            "policies": {"tools": {"allowed": []}}
        }
        # Should not raise
        metadata = Metadata.model_validate(data["metadata"])
        assert metadata.tags == []
        
        policies = Policies.model_validate(data["policies"])
        assert policies.tools.allowed == []
    
    def test_io_schema_empty(self):
        """Test with empty I/O schema"""
        data = {}
        io_schema = IOSchema.model_validate(data)
        assert io_schema.input is None
        assert io_schema.output is None


# =============================================================================
# I/O SCHEMA VALIDATION TESTS
# =============================================================================

class TestIOSchema:
    """Test I/O schema validation"""
    
    def test_basic_io_schema(self):
        """Test basic I/O schema with object types"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"}
                },
                "required": ["query"]
            },
            "output": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"}
                }
            }
        }
        schema = IOSchema.model_validate(data)
        assert schema.input.type == "object"
        assert "query" in schema.input.properties
        assert schema.input.required == ["query"]
    
    def test_nested_object_properties(self):
        """Test nested objects in properties"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"}
                        }
                    }
                }
            }
        }
        schema = IOSchema.model_validate(data)
        assert "user" in schema.input.properties
        assert schema.input.properties["user"]["type"] == "object"
    
    def test_array_type_with_items(self):
        """Test array type with items definition"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
        schema = IOSchema.model_validate(data)
        assert schema.input.properties["tags"]["type"] == "array"
        assert "items" in schema.input.properties["tags"]
    
    def test_array_type_without_items_fails(self):
        """Test array type without items fails validation"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array"
                        # Missing items
                    }
                }
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "missing 'items'" in str(exc_info.value).lower()
    
    def test_root_array_type(self):
        """Test root-level array type"""
        data = {
            "input": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
        schema = IOSchema.model_validate(data)
        assert schema.input.type == "array"
        assert schema.input.items is not None
    
    def test_root_array_without_items_fails(self):
        """Test root-level array without items fails"""
        data = {
            "input": {
                "type": "array"
                # Missing items
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "requires 'items'" in str(exc_info.value).lower()
    
    def test_unsupported_json_schema_type(self):
        """Test unsupported JSON Schema type fails"""
        data = {
            "input": {
                "type": "custom_type"  # Invalid
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "unsupported" in str(exc_info.value).lower()
    
    def test_unsupported_property_type(self):
        """Test unsupported property type fails"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "field": {"type": "weird_type"}
                }
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "unsupported type" in str(exc_info.value).lower()
    
    def test_property_not_dict_fails(self):
        """Test property that's not a dict fails"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "field": "string"  # Should be {"type": "string"}
                }
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "must be a JSON Schema object" in str(exc_info.value)
    
    def test_empty_property_name_fails(self):
        """Test empty property name fails"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "": {"type": "string"}  # Empty name
                }
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_whitespace_property_name_fails(self):
        """Test whitespace-only property name fails"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "   ": {"type": "string"}  # Whitespace only
                }
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_required_field_not_in_properties(self):
        """Test required field that doesn't exist in properties fails"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"}
                },
                "required": ["field2"]  # field2 doesn't exist
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "not defined in properties" in str(exc_info.value).lower()
    
    def test_duplicate_required_fields(self):
        """Test duplicate fields in required list fails"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"}
                },
                "required": ["field1", "field1"]  # Duplicate
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            IOSchema.model_validate(data)
        assert "duplicate" in str(exc_info.value).lower()
    
    def test_all_json_schema_types(self):
        """Test all supported JSON Schema types"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "str_field": {"type": "string"},
                    "num_field": {"type": "number"},
                    "int_field": {"type": "integer"},
                    "bool_field": {"type": "boolean"},
                    "arr_field": {"type": "array", "items": {"type": "string"}},
                    "obj_field": {"type": "object"},
                    "null_field": {"type": "null"}
                }
            }
        }
        schema = IOSchema.model_validate(data)
        assert len(schema.input.properties) == 7
    
    def test_complex_nested_schema(self):
        """Test complex nested schema with arrays of objects"""
        data = {
            "input": {
                "type": "object",
                "properties": {
                    "users": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "emails": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
        schema = IOSchema.model_validate(data)
        users_prop = schema.input.properties["users"]
        assert users_prop["type"] == "array"
        assert users_prop["items"]["type"] == "object"
    
    def test_io_schema_with_description(self):
        """Test I/O schema with description field"""
        data = {
            "input": {
                "type": "object",
                "description": "Input parameters for the agent",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }
        schema = IOSchema.model_validate(data)
        assert schema.input.description == "Input parameters for the agent"

