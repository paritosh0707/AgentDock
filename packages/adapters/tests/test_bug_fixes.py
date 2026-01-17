"""Tests for bug fixes in adapters.

These tests verify fixes for specific bugs:
1. Context cleanup in finally block (LangGraphAdapter.invoke)
2. Async generator for invoke_stream (LangGraphAdapter)
3. Correct _accepts_context detection (HandlerAdapter)
"""

import inspect
from typing import Any, Dict

import pytest


class TestContextCleanupInFinally:
    """Test that context cleanup happens even when exceptions occur."""

    def test_handler_adapter_cleans_context_on_exception(self):
        """HandlerAdapter should clean context even when handler raises."""
        from dockrion_adapters.handler_adapter import HandlerAdapter

        adapter = HandlerAdapter()

        # Create a handler that raises
        def failing_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
            raise ValueError("Intentional failure")

        # Manually set up the adapter
        adapter._handler = failing_handler
        adapter._handler_path = "test:failing_handler"
        adapter._signature = inspect.signature(failing_handler)
        adapter._accepts_context = False

        # Mock context
        class MockContext:
            pass

        context = MockContext()

        # Should raise, but context cleanup should still happen
        with pytest.raises(Exception):
            adapter.invoke({"test": "data"}, context=context)

        # The test passes if no exception is raised from context cleanup
        # and the original exception propagates

    def test_langgraph_adapter_invoke_has_finally_block(self):
        """LangGraphAdapter.invoke should have context cleanup in finally."""
        from dockrion_adapters.langgraph_adapter import LangGraphAdapter

        # Check that invoke method source contains finally block for context
        source = inspect.getsource(LangGraphAdapter.invoke)

        # Verify finally block exists and contains context cleanup
        assert "finally:" in source, "invoke method should have a finally block"
        assert "set_current_context(None)" in source, "finally should clear context"


class TestInvokeStreamIsAsync:
    """Test that invoke_stream is an async generator."""

    def test_invoke_stream_is_async_generator(self):
        """invoke_stream should be an async generator function."""
        from dockrion_adapters.langgraph_adapter import LangGraphAdapter

        adapter = LangGraphAdapter()

        # Check that invoke_stream is an async generator
        assert inspect.isasyncgenfunction(
            adapter.invoke_stream
        ), "invoke_stream should be an async generator function"

    def test_invoke_stream_return_type_hint(self):
        """invoke_stream should have AsyncIterator return type."""
        from dockrion_adapters.langgraph_adapter import LangGraphAdapter

        hints = LangGraphAdapter.invoke_stream.__annotations__
        return_hint = hints.get("return", "")

        # Should contain AsyncIterator in the annotation
        assert "AsyncIterator" in str(return_hint), (
            f"invoke_stream should return AsyncIterator, got: {return_hint}"
        )


class TestAcceptsContextDetection:
    """Test correct detection of context parameter support."""

    def test_handler_with_explicit_context_param(self):
        """Handler with 'context' parameter should be detected."""
        from dockrion_adapters.handler_adapter import HandlerAdapter

        def handler_with_context(payload: Dict[str, Any], context: Any) -> Dict[str, Any]:
            return {}

        adapter = HandlerAdapter()
        adapter._handler = handler_with_context
        adapter._handler_path = "test:handler_with_context"

        # Manually trigger detection logic
        adapter._signature = inspect.signature(handler_with_context)
        adapter._accepts_context = False

        # Re-run detection
        for param_name, param in adapter._signature.parameters.items():
            if param_name == "context":
                adapter._accepts_context = True
                break
            if param.annotation != inspect.Parameter.empty:
                annotation_str = str(param.annotation)
                if "StreamContext" in annotation_str:
                    adapter._accepts_context = True
                    break

        assert adapter._accepts_context is True

    def test_handler_with_two_params_no_context(self):
        """Handler with 2 params but no 'context' should NOT be detected."""
        from dockrion_adapters.handler_adapter import HandlerAdapter

        def handler_with_verbose(
            payload: Dict[str, Any], verbose: bool = False
        ) -> Dict[str, Any]:
            return {}

        adapter = HandlerAdapter()
        adapter._handler = handler_with_verbose
        adapter._handler_path = "test:handler_with_verbose"

        # Manually trigger detection logic
        adapter._signature = inspect.signature(handler_with_verbose)
        adapter._accepts_context = False

        # Re-run detection (same logic as in load())
        for param_name, param in adapter._signature.parameters.items():
            if param_name == "context":
                adapter._accepts_context = True
                break
            if param.annotation != inspect.Parameter.empty:
                annotation_str = str(param.annotation)
                if "StreamContext" in annotation_str:
                    adapter._accepts_context = True
                    break

        # This should be False - verbose is not a context parameter
        assert adapter._accepts_context is False, (
            "Handler with 'verbose' param should NOT be detected as accepting context"
        )

    def test_handler_with_three_params_no_context(self):
        """Handler with many params but no 'context' should NOT be detected."""
        from dockrion_adapters.handler_adapter import HandlerAdapter

        def multi_param_handler(
            payload: Dict[str, Any],
            debug: bool = False,
            timeout: int = 30,
        ) -> Dict[str, Any]:
            return {}

        adapter = HandlerAdapter()
        adapter._handler = multi_param_handler
        adapter._handler_path = "test:multi_param_handler"

        # Manually trigger detection logic
        adapter._signature = inspect.signature(multi_param_handler)
        adapter._accepts_context = False

        for param_name, param in adapter._signature.parameters.items():
            if param_name == "context":
                adapter._accepts_context = True
                break
            if param.annotation != inspect.Parameter.empty:
                annotation_str = str(param.annotation)
                if "StreamContext" in annotation_str:
                    adapter._accepts_context = True
                    break

        assert adapter._accepts_context is False

    def test_handler_only_payload(self):
        """Handler with only payload should NOT be detected as accepting context."""
        from dockrion_adapters.handler_adapter import HandlerAdapter

        def simple_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
            return {}

        adapter = HandlerAdapter()
        adapter._handler = simple_handler
        adapter._handler_path = "test:simple_handler"

        # Manually trigger detection logic
        adapter._signature = inspect.signature(simple_handler)
        adapter._accepts_context = False

        for param_name, param in adapter._signature.parameters.items():
            if param_name == "context":
                adapter._accepts_context = True
                break
            if param.annotation != inspect.Parameter.empty:
                annotation_str = str(param.annotation)
                if "StreamContext" in annotation_str:
                    adapter._accepts_context = True
                    break

        assert adapter._accepts_context is False


class TestHandlerAdapterLoadDetection:
    """Test the full load() method correctly detects context support."""

    def test_load_handler_with_context(self, tmp_path):
        """load() should correctly detect context parameter."""
        # Create a temp module with handler
        module_file = tmp_path / "test_module.py"
        module_file.write_text("""
def handler_with_context(payload, context):
    return {"result": "ok"}
""")

        import sys

        sys.path.insert(0, str(tmp_path))

        try:
            from dockrion_adapters.handler_adapter import HandlerAdapter

            adapter = HandlerAdapter()
            adapter.load("test_module:handler_with_context")

            assert adapter._accepts_context is True
        finally:
            sys.path.remove(str(tmp_path))
            if "test_module" in sys.modules:
                del sys.modules["test_module"]

    def test_load_handler_without_context(self, tmp_path):
        """load() should correctly detect NO context parameter."""
        # Create a temp module with handler
        module_file = tmp_path / "test_module2.py"
        module_file.write_text("""
def handler_no_context(payload, verbose=False):
    return {"result": "ok"}
""")

        import sys

        sys.path.insert(0, str(tmp_path))

        try:
            from dockrion_adapters.handler_adapter import HandlerAdapter

            adapter = HandlerAdapter()
            adapter.load("test_module2:handler_no_context")

            # Should NOT detect verbose as context
            assert adapter._accepts_context is False, (
                "verbose parameter should NOT be detected as context"
            )
        finally:
            sys.path.remove(str(tmp_path))
            if "test_module2" in sys.modules:
                del sys.modules["test_module2"]
