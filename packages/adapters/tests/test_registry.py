"""
Tests for adapter registry and factory.

Tests:
- get_adapter() returns correct adapter
- Unsupported frameworks raise errors
- Custom adapter registration
- Framework listing and checking
"""

import pytest
from agentdock_adapters import (
    get_adapter,
    register_adapter,
    list_supported_frameworks,
    is_framework_supported,
    get_adapter_info,
    LangGraphAdapter,
)
from agentdock_common import ValidationError


# =============================================================================
# GET_ADAPTER TESTS
# =============================================================================

class TestGetAdapter:
    """Test get_adapter factory function"""
    
    def test_get_langgraph_adapter(self):
        """Test getting LangGraph adapter"""
        adapter = get_adapter("langgraph")
        
        assert isinstance(adapter, LangGraphAdapter)
        assert adapter._runner is None  # Not loaded yet
    
    def test_get_adapter_case_insensitive(self):
        """Test framework name is case-insensitive"""
        adapters = [
            get_adapter("langgraph"),
            get_adapter("LangGraph"),
            get_adapter("LANGGRAPH"),
            get_adapter("  langgraph  "),  # with whitespace
        ]
        
        # All should be LangGraphAdapter instances
        for adapter in adapters:
            assert isinstance(adapter, LangGraphAdapter)
    
    def test_get_adapter_unsupported_framework(self):
        """Test error with unsupported framework"""
        with pytest.raises(ValidationError) as exc:
            get_adapter("unsupported")
        
        assert "unsupported" in str(exc.value).lower()
        assert "supported" in str(exc.value).lower()
    
    def test_get_adapter_returns_new_instance(self):
        """Test each call returns new adapter instance"""
        adapter1 = get_adapter("langgraph")
        adapter2 = get_adapter("langgraph")
        
        # Different instances
        assert adapter1 is not adapter2
        
        # But same type
        assert type(adapter1) == type(adapter2)
    
    def test_get_adapter_error_includes_supported_list(self):
        """Test error message includes list of supported frameworks"""
        try:
            get_adapter("unsupported")
        except ValidationError as e:
            assert "langgraph" in str(e).lower()


# =============================================================================
# REGISTER_ADAPTER TESTS
# =============================================================================

class TestRegisterAdapter:
    """Test custom adapter registration"""
    
    def test_register_custom_adapter(self):
        """Test registering custom adapter"""
        class CustomAdapter:
            def load(self, entrypoint): pass
            def invoke(self, payload): return {"custom": True}
            def get_metadata(self): return {"framework": "custom"}
        
        register_adapter("custom", CustomAdapter)
        
        # Should now be available
        adapter = get_adapter("custom")
        assert isinstance(adapter, CustomAdapter)
    
    def test_register_adapter_missing_method(self):
        """Test error when adapter missing required methods"""
        class IncompleteAdapter:
            def load(self, entrypoint): pass
            # Missing invoke() and get_metadata()
        
        with pytest.raises(ValueError) as exc:
            register_adapter("incomplete", IncompleteAdapter)
        
        assert "implement" in str(exc.value).lower()
    
    def test_register_adapter_overrides_existing(self):
        """Test registering adapter overrides existing one"""
        class NewLangGraphAdapter:
            def load(self, entrypoint): pass
            def invoke(self, payload): return {"new": True}
            def get_metadata(self): return {"framework": "langgraph-new"}
        
        # Register override
        register_adapter("langgraph", NewLangGraphAdapter)
        
        # Get adapter should return new one
        adapter = get_adapter("langgraph")
        assert isinstance(adapter, NewLangGraphAdapter)
        
        # Restore original (cleanup)
        register_adapter("langgraph", LangGraphAdapter)


# =============================================================================
# LIST_SUPPORTED_FRAMEWORKS TESTS
# =============================================================================

class TestListSupportedFrameworks:
    """Test listing supported frameworks"""
    
    def test_list_supported_frameworks(self):
        """Test getting list of supported frameworks"""
        frameworks = list_supported_frameworks()
        
        assert isinstance(frameworks, list)
        assert "langgraph" in frameworks
    
    def test_list_is_sorted(self):
        """Test list is sorted alphabetically"""
        frameworks = list_supported_frameworks()
        
        assert frameworks == sorted(frameworks)
    
    def test_list_after_registration(self):
        """Test list includes registered frameworks"""
        class TestAdapter:
            def load(self, entrypoint): pass
            def invoke(self, payload): return {}
            def get_metadata(self): return {}
        
        register_adapter("testframework", TestAdapter)
        
        frameworks = list_supported_frameworks()
        assert "testframework" in frameworks


# =============================================================================
# IS_FRAMEWORK_SUPPORTED TESTS
# =============================================================================

class TestIsFrameworkSupported:
    """Test checking if framework is supported"""
    
    def test_is_framework_supported_true(self):
        """Test returns True for supported framework"""
        assert is_framework_supported("langgraph") is True
    
    def test_is_framework_supported_false(self):
        """Test returns False for unsupported framework"""
        assert is_framework_supported("unsupported") is False
    
    def test_is_framework_supported_case_insensitive(self):
        """Test check is case-insensitive"""
        assert is_framework_supported("LangGraph") is True
        assert is_framework_supported("LANGGRAPH") is True
        assert is_framework_supported("  langgraph  ") is True


# =============================================================================
# GET_ADAPTER_INFO TESTS
# =============================================================================

class TestGetAdapterInfo:
    """Test getting adapter information"""
    
    def test_get_adapter_info_langgraph(self):
        """Test getting info for LangGraph adapter"""
        info = get_adapter_info("langgraph")
        
        assert info["framework"] == "langgraph"
        assert info["adapter_class"] == "LangGraphAdapter"
        assert info["supported"] is True
        assert "module" in info
    
    def test_get_adapter_info_unsupported(self):
        """Test error for unsupported framework"""
        with pytest.raises(ValidationError) as exc:
            get_adapter_info("unsupported")
        
        assert "unsupported" in str(exc.value).lower()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestRegistryIntegration:
    """Test complete registry workflows"""
    
    def test_full_custom_adapter_workflow(self):
        """Test registering and using custom adapter"""
        # 1. Define custom adapter
        class MyFrameworkAdapter:
            def __init__(self):
                self._runner = None
            
            def load(self, entrypoint):
                self._runner = "loaded"
            
            def invoke(self, payload):
                return {"framework": "myframework", "input": payload}
            
            def get_metadata(self):
                return {
                    "framework": "myframework",
                    "loaded": self._runner is not None
                }
        
        # 2. Register adapter
        register_adapter("myframework", MyFrameworkAdapter)
        
        # 3. Check it's supported
        assert is_framework_supported("myframework") is True
        assert "myframework" in list_supported_frameworks()
        
        # 4. Get adapter info
        info = get_adapter_info("myframework")
        assert info["framework"] == "myframework"
        
        # 5. Use adapter
        adapter = get_adapter("myframework")
        adapter.load("fake:entrypoint")
        result = adapter.invoke({"test": "data"})
        
        # 6. Verify it works
        assert result["framework"] == "myframework"
        assert result["input"]["test"] == "data"

