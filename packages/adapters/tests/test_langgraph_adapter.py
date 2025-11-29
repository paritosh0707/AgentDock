"""
Tests for LangGraphAdapter.

Comprehensive test coverage for:
- Loading success and failures
- Invocation success and failures
- Metadata extraction
- Health checks
- Error handling
"""

import pytest
from dockrion_adapters import LangGraphAdapter
from dockrion_adapters.errors import (
    AdapterLoadError,
    ModuleNotFoundError,
    CallableNotFoundError,
    InvalidAgentError,
    AdapterNotLoadedError,
    AgentExecutionError,
    InvalidOutputError,
)


# =============================================================================
# LOADING TESTS
# =============================================================================

class TestLoading:
    """Test agent loading functionality"""
    
    def test_load_simple_agent(self):
        """Test loading valid simple agent"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        assert adapter._runner is not None
        assert adapter._entrypoint == "tests.fixtures.sample_agents:build_simple_agent"
    
    def test_load_echo_agent(self):
        """Test loading echo agent"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_echo_agent")
        
        assert adapter._runner is not None
        metadata = adapter.get_metadata()
        assert metadata["loaded"] is True
    
    def test_load_module_not_found(self):
        """Test error when module doesn't exist"""
        adapter = LangGraphAdapter()
        
        with pytest.raises(ModuleNotFoundError) as exc:
            adapter.load("nonexistent.module:build_agent")
        
        assert "nonexistent.module" in str(exc.value)
        assert "not found" in str(exc.value).lower()
    
    def test_load_callable_not_found(self):
        """Test error when callable doesn't exist in module"""
        adapter = LangGraphAdapter()
        
        with pytest.raises(CallableNotFoundError) as exc:
            adapter.load("tests.fixtures.sample_agents:nonexistent_function")
        
        assert "nonexistent_function" in str(exc.value)
        assert "no function" in str(exc.value).lower()
    
    def test_load_invalid_entrypoint_format(self):
        """Test error with invalid entrypoint format"""
        adapter = LangGraphAdapter()
        
        # Missing colon
        with pytest.raises(AdapterLoadError):
            adapter.load("module_without_colon")
        
        # Empty string
        with pytest.raises(AdapterLoadError):
            adapter.load("")
    
    def test_load_factory_crashes(self):
        """Test error when factory function crashes"""
        adapter = LangGraphAdapter()
        
        with pytest.raises(AdapterLoadError) as exc:
            adapter.load("tests.fixtures.sample_agents:build_failing_factory")
        
        assert "failed" in str(exc.value).lower()
    
    def test_load_agent_without_invoke(self):
        """Test error when agent missing .invoke() method"""
        adapter = LangGraphAdapter()
        
        with pytest.raises(InvalidAgentError) as exc:
            adapter.load("tests.fixtures.sample_agents:build_agent_without_invoke")
        
        assert "invoke" in str(exc.value).lower()
        assert "method" in str(exc.value).lower()
    
    def test_load_detects_streaming_support(self):
        """Test detection of streaming capability"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_streaming_agent")
        
        assert adapter._supports_streaming is True
        metadata = adapter.get_metadata()
        assert metadata["supports_streaming"] is True
    
    def test_load_detects_async_support(self):
        """Test detection of async capability"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_async_agent")
        
        assert adapter._supports_async is True
        metadata = adapter.get_metadata()
        assert metadata["supports_async"] is True


# =============================================================================
# INVOCATION TESTS
# =============================================================================

class TestInvocation:
    """Test agent invocation functionality"""
    
    def test_invoke_simple_agent(self):
        """Test successful invocation"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        result = adapter.invoke({"input": "test data"})
        
        assert isinstance(result, dict)
        assert "output" in result
        assert "test data" in result["output"]
    
    def test_invoke_echo_agent(self):
        """Test invocation returns correct output"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_echo_agent")
        
        payload = {"query": "hello", "user": "alice"}
        result = adapter.invoke(payload)
        
        assert isinstance(result, dict)
        assert "echo" in result
        assert result["echo"] == payload
    
    def test_invoke_before_load(self):
        """Test error when invoking before loading"""
        adapter = LangGraphAdapter()
        
        with pytest.raises(AdapterNotLoadedError) as exc:
            adapter.invoke({"input": "test"})
        
        assert "not loaded" in str(exc.value).lower()
    
    def test_invoke_agent_crashes(self):
        """Test error when agent crashes during invocation"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_crashing_agent")
        
        with pytest.raises(AgentExecutionError) as exc:
            adapter.invoke({"input": "test"})
        
        assert "crashed intentionally" in str(exc.value).lower()
    
    def test_invoke_invalid_output_type(self):
        """Test error when agent returns non-dict"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_invalid_output_agent")
        
        with pytest.raises(InvalidOutputError) as exc:
            adapter.invoke({"input": "test"})
        
        assert "dict" in str(exc.value).lower()
        assert "string" in str(exc.value).lower() or "str" in str(exc.value).lower()
    
    def test_invoke_multiple_times(self):
        """Test multiple invocations work"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        # First invocation
        result1 = adapter.invoke({"input": "first"})
        assert "first" in result1["output"]
        
        # Second invocation
        result2 = adapter.invoke({"input": "second"})
        assert "second" in result2["output"]
        
        # Results are independent
        assert result1 != result2
    
    def test_invoke_with_empty_payload(self):
        """Test invocation with empty dict"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        result = adapter.invoke({})
        
        assert isinstance(result, dict)
        assert "output" in result


# =============================================================================
# METADATA TESTS
# =============================================================================

class TestMetadata:
    """Test metadata extraction"""
    
    def test_metadata_before_load(self):
        """Test metadata when adapter not loaded"""
        adapter = LangGraphAdapter()
        metadata = adapter.get_metadata()
        
        assert metadata["framework"] == "langgraph"
        assert metadata["loaded"] is False
        assert metadata["agent_type"] is None
        assert metadata["entrypoint"] is None
    
    def test_metadata_after_load(self):
        """Test metadata after loading agent"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        metadata = adapter.get_metadata()
        
        assert metadata["framework"] == "langgraph"
        assert metadata["loaded"] is True
        assert metadata["agent_type"] == "SimpleAgent"
        assert metadata["entrypoint"] == "tests.fixtures.sample_agents:build_simple_agent"
        assert "adapter_version" in metadata
    
    def test_metadata_includes_capabilities(self):
        """Test metadata includes capability flags"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_streaming_agent")
        
        metadata = adapter.get_metadata()
        
        assert "supports_streaming" in metadata
        assert "supports_async" in metadata
        assert metadata["supports_streaming"] is True


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

class TestHealthCheck:
    """Test health check functionality"""
    
    def test_health_check_before_load(self):
        """Test health check fails when not loaded"""
        adapter = LangGraphAdapter()
        assert adapter.health_check() is False
    
    def test_health_check_after_load(self):
        """Test health check passes after loading"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        # Health check should pass
        assert adapter.health_check() is True
    
    def test_health_check_with_crashing_agent(self):
        """Test health check fails for crashing agent"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_crashing_agent")
        
        # Health check should fail
        assert adapter.health_check() is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """End-to-end integration tests"""
    
    def test_full_workflow(self):
        """Test complete load -> invoke -> metadata workflow"""
        # 1. Create adapter
        adapter = LangGraphAdapter()
        
        # 2. Check initial state
        assert adapter.get_metadata()["loaded"] is False
        
        # 3. Load agent
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        # 4. Check loaded state
        assert adapter.get_metadata()["loaded"] is True
        assert adapter.health_check() is True
        
        # 5. Invoke agent
        result = adapter.invoke({"input": "integration test"})
        
        # 6. Verify result
        assert isinstance(result, dict)
        assert "output" in result
        assert "integration test" in result["output"]
    
    def test_load_different_agents(self):
        """Test loading different agents with same adapter instance"""
        adapter = LangGraphAdapter()
        
        # Load first agent
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        result1 = adapter.invoke({"input": "test"})
        assert "output" in result1
        
        # Load second agent (replaces first)
        adapter.load("tests.fixtures.sample_agents:build_echo_agent")
        result2 = adapter.invoke({"input": "test"})
        assert "echo" in result2
        
        # Results are different (different agents)
        assert result1 != result2


# =============================================================================
# CONFIG PARAMETER TESTS
# =============================================================================

class TestConfigParameter:
    """Test config parameter support"""
    
    def test_invoke_with_config(self):
        """Test invocation with config parameter"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_config_agent")
        
        # Invoke with config
        result = adapter.invoke(
            {"input": "test"},
            config={"thread_id": "thread-123", "recursion_limit": 50}
        )
        
        assert result["config_received"] is True
        assert result["thread_id"] == "thread-123"
        assert result["recursion_limit"] == 50
    
    def test_invoke_without_config(self):
        """Test invocation without config (backward compatible)"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_config_agent")
        
        # Invoke without config
        result = adapter.invoke({"input": "test"})
        
        assert result["config_received"] is False
    
    def test_config_support_detection(self):
        """Test adapter detects config support"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_config_agent")
        
        metadata = adapter.get_metadata()
        assert metadata["supports_config"] is True
    
    def test_config_with_non_supporting_agent(self):
        """Test config gracefully ignored for agents without config support"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        # Metadata should show no config support
        metadata = adapter.get_metadata()
        assert metadata["supports_config"] is False
        
        # Config should be ignored (no error)
        result = adapter.invoke(
            {"input": "test"},
            config={"thread_id": "123"}
        )
        assert "output" in result
    
    def test_stateful_agent_with_config(self):
        """Test stateful agent maintains state across invocations"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_stateful_agent")
        
        # First invocation
        result1 = adapter.invoke(
            {"input": "first"},
            config={"thread_id": "conv-1"}
        )
        assert "history" in result1
        assert len(result1["history"]) == 1
        
        # Second invocation (same thread)
        result2 = adapter.invoke(
            {"input": "second"},
            config={"thread_id": "conv-1"}
        )
        assert len(result2["history"]) == 2
        
        # Different thread (separate state)
        result3 = adapter.invoke(
            {"input": "first"},
            config={"thread_id": "conv-2"}
        )
        assert len(result3["history"]) == 1


# =============================================================================
# STRICT VALIDATION TESTS
# =============================================================================

class TestStrictValidation:
    """Test strict validation mode"""
    
    def test_adapter_with_strict_validation_enabled(self):
        """Test creating adapter with strict validation"""
        adapter = LangGraphAdapter(strict_validation=True)
        
        metadata = adapter.get_metadata()
        assert metadata["strict_validation"] is True
    
    def test_adapter_default_no_strict_validation(self):
        """Test default is no strict validation"""
        adapter = LangGraphAdapter()
        
        metadata = adapter.get_metadata()
        assert metadata["strict_validation"] is False
    
    def test_strict_validation_with_mock_agent(self):
        """Test strict validation fails gracefully when langgraph not installed"""
        adapter = LangGraphAdapter(strict_validation=True)
        
        # Load mock agent (not real LangGraph)
        # Should fall back to duck typing when langgraph not installed
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        # Should still work
        result = adapter.invoke({"input": "test"})
        assert "output" in result


# =============================================================================
# METADATA TESTS (EXTENDED)
# =============================================================================

class TestMetadataExtended:
    """Test extended metadata fields"""
    
    def test_metadata_includes_agent_module(self):
        """Test metadata includes agent module path"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        metadata = adapter.get_metadata()
        assert "agent_module" in metadata
        assert metadata["agent_module"] is not None
    
    def test_metadata_includes_supports_config(self):
        """Test metadata includes config support flag"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_config_agent")
        
        metadata = adapter.get_metadata()
        assert "supports_config" in metadata
        assert metadata["supports_config"] is True
    
    def test_metadata_includes_is_langgraph_type(self):
        """Test metadata includes langgraph type check"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        metadata = adapter.get_metadata()
        assert "is_langgraph_type" in metadata
        # Mock agents won't be langgraph types
        assert metadata["is_langgraph_type"] is False
    
    def test_metadata_before_load_includes_new_fields(self):
        """Test metadata has new fields even before loading"""
        adapter = LangGraphAdapter(strict_validation=True)
        
        metadata = adapter.get_metadata()
        assert metadata["strict_validation"] is True
        assert metadata["supports_config"] is False
        assert metadata["is_langgraph_type"] is None


# =============================================================================
# SIGNATURE VALIDATION TESTS
# =============================================================================

class TestSignatureValidation:
    """Test invoke() signature validation"""
    
    def test_signature_validation_detects_config_support(self):
        """Test signature validation correctly detects config parameter"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_config_agent")
        
        assert adapter._supports_config is True
    
    def test_signature_validation_no_config_support(self):
        """Test signature validation detects no config support"""
        adapter = LangGraphAdapter()
        adapter.load("tests.fixtures.sample_agents:build_simple_agent")
        
        # Simple agent has no config parameter
        assert adapter._supports_config is False


# =============================================================================
# ERROR MESSAGE TESTS
# =============================================================================

class TestErrorMessages:
    """Test error messages are helpful"""
    
    def test_module_not_found_has_hint(self):
        """Test ModuleNotFoundError includes helpful hint"""
        adapter = LangGraphAdapter()
        
        try:
            adapter.load("nonexistent.module:build")
        except ModuleNotFoundError as e:
            assert "hint" in str(e).lower() or "ensure" in str(e).lower()
    
    def test_callable_not_found_shows_available(self):
        """Test CallableNotFoundError mentions checking function name"""
        adapter = LangGraphAdapter()
        
        try:
            adapter.load("tests.fixtures.sample_agents:nonexistent")
        except CallableNotFoundError as e:
            assert "check" in str(e).lower() or "available" in str(e).lower()
    
    def test_invalid_agent_has_hint(self):
        """Test InvalidAgentError includes hint"""
        adapter = LangGraphAdapter()
        
        try:
            adapter.load("tests.fixtures.sample_agents:build_agent_without_invoke")
        except InvalidAgentError as e:
            assert "hint" in str(e).lower() or "ensure" in str(e).lower()
    
    def test_not_loaded_error_is_clear(self):
        """Test AdapterNotLoadedError message is clear"""
        adapter = LangGraphAdapter()
        
        try:
            adapter.invoke({})
        except AdapterNotLoadedError as e:
            assert "load" in str(e).lower()
            assert "before" in str(e).lower() or "first" in str(e).lower()

