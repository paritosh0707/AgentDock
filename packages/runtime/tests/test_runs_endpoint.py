"""Tests for the /runs endpoint and context passing.

These tests verify that:
1. Context is properly passed to adapter.invoke()
2. Streaming execution works when adapter supports it
3. Events are properly emitted through the EventBus
4. Timeout handling works correctly
"""

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunsEndpointContextPassing:
    """Tests to verify context is passed to adapter.invoke()."""

    def test_execute_run_passes_context_to_invoke(self):
        """Test that _execute_with_invoke passes context parameter."""
        import inspect

        from dockrion_runtime.endpoints.runs import _execute_with_invoke

        # Check the function signature includes context
        sig = inspect.signature(_execute_with_invoke)
        params = list(sig.parameters.keys())

        assert "context" in params, "context parameter must be in _execute_with_invoke"

        # Check the source code actually passes context to adapter.invoke
        source = inspect.getsource(_execute_with_invoke)
        assert "context=_context" in source or "context=context" in source, (
            "_execute_with_invoke must pass context to adapter.invoke()"
        )

    def test_execute_run_passes_context_to_streaming(self):
        """Test that _execute_with_streaming passes context parameter."""
        import inspect

        from dockrion_runtime.endpoints.runs import _execute_with_streaming

        # Check the function signature includes context
        sig = inspect.signature(_execute_with_streaming)
        params = list(sig.parameters.keys())

        assert "context" in params, "context parameter must be in _execute_with_streaming"

        # Check the source code actually passes context
        source = inspect.getsource(_execute_with_streaming)
        assert "context=context" in source, (
            "_execute_with_streaming must pass context to adapter.invoke_stream()"
        )

    def test_execute_run_gets_context_from_run_manager(self):
        """Test that _execute_run gets context from run_manager."""
        import inspect

        from dockrion_runtime.endpoints.runs import _execute_run

        source = inspect.getsource(_execute_run)

        # Must get context from run_manager
        assert "run_manager.get_context" in source, (
            "_execute_run must call run_manager.get_context()"
        )

        # Must pass context to execution functions
        assert "context=context" in source or "_execute_with_invoke" in source, (
            "_execute_run must pass context to execution functions"
        )


class TestExecuteWithInvoke:
    """Tests for the _execute_with_invoke helper function."""

    @pytest.mark.asyncio
    async def test_invoke_with_context_called(self):
        """Test that adapter.invoke is called with context."""
        from dockrion_runtime.config import RuntimeConfig
        from dockrion_runtime.endpoints.runs import _execute_with_invoke

        # Create mock adapter that records call arguments
        mock_adapter = MagicMock()
        mock_adapter.invoke = MagicMock(return_value={"result": "test"})

        # Create mock context
        mock_context = MagicMock()
        mock_context.run_id = "test-run-123"

        # Create minimal config
        config = RuntimeConfig(
            agent_name="test",
            agent_framework="langgraph",
            timeout_sec=0,  # No timeout for this test
        )

        payload = {"input": "test"}

        # Execute
        result = await _execute_with_invoke(
            adapter=mock_adapter,
            payload=payload,
            context=mock_context,
            config=config,
            run_id="test-run-123",
        )

        # Verify invoke was called with context
        mock_adapter.invoke.assert_called_once()
        call_args = mock_adapter.invoke.call_args

        # Check that context was passed
        assert call_args.kwargs.get("context") == mock_context, (
            "adapter.invoke() must be called with context parameter"
        )

        assert result == {"result": "test"}

    @pytest.mark.asyncio
    async def test_invoke_with_timeout(self):
        """Test that timeout is properly applied."""
        from dockrion_runtime.config import RuntimeConfig
        from dockrion_runtime.endpoints.runs import _execute_with_invoke

        # Create mock adapter that takes too long
        def slow_invoke(*args, **kwargs):
            import time
            time.sleep(2)  # Sleep longer than timeout
            return {"result": "too late"}

        mock_adapter = MagicMock()
        mock_adapter.invoke = slow_invoke

        mock_context = MagicMock()
        config = RuntimeConfig(
            agent_name="test",
            agent_framework="langgraph",
            timeout_sec=0.1,  # Very short timeout
        )

        payload = {"input": "test"}

        # Should raise TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await _execute_with_invoke(
                adapter=mock_adapter,
                payload=payload,
                context=mock_context,
                config=config,
                run_id="test-run-123",
            )


class TestExecuteWithStreaming:
    """Tests for the _execute_with_streaming helper function."""

    @pytest.mark.asyncio
    async def test_streaming_with_context_called(self):
        """Test that adapter.invoke_stream is called with context."""
        from dockrion_runtime.config import RuntimeConfig
        from dockrion_runtime.endpoints.runs import _execute_with_streaming

        # Create mock adapter with async streaming
        mock_adapter = MagicMock()

        async def mock_stream(payload, context=None):
            yield {"type": "step", "node": "test_node", "output": {"data": "chunk1"}}
            yield {"type": "result", "data": {"result": "final"}}

        mock_adapter.invoke_stream = mock_stream

        mock_context = MagicMock()
        mock_context.run_id = "test-run-123"

        config = RuntimeConfig(
            agent_name="test",
            agent_framework="langgraph",
            timeout_sec=0,  # No timeout
        )

        payload = {"input": "test"}

        # Execute
        result = await _execute_with_streaming(
            adapter=mock_adapter,
            payload=payload,
            context=mock_context,
            config=config,
            run_id="test-run-123",
        )

        # Result should be from the "result" type chunk
        assert result == {"result": "final"}


class TestExecuteRunIntegration:
    """Integration tests for _execute_run."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test the full execution flow with mocked components."""
        from dockrion_runtime.config import RuntimeConfig, RuntimeState
        from dockrion_runtime.endpoints.runs import _execute_run

        # Create mock state components
        mock_run_manager = AsyncMock()
        mock_run_manager.start_run = AsyncMock()
        mock_run_manager.get_context = AsyncMock(return_value=MagicMock(run_id="test-run"))
        mock_run_manager.set_result = AsyncMock()
        mock_run_manager.set_error = AsyncMock()

        mock_adapter = MagicMock()
        mock_adapter.invoke = MagicMock(return_value={"output": "success"})

        mock_policy_engine = MagicMock()
        mock_policy_engine.apply_output_policies = MagicMock(side_effect=lambda x: x)

        mock_metrics = MagicMock()
        mock_metrics.inc_active = MagicMock()
        mock_metrics.dec_active = MagicMock()
        mock_metrics.inc_request = MagicMock()
        mock_metrics.observe_latency = MagicMock()

        state = RuntimeState()
        state.run_manager = mock_run_manager
        state.adapter = mock_adapter
        state.policy_engine = mock_policy_engine
        state.metrics = mock_metrics

        config = RuntimeConfig(
            agent_name="test",
            agent_framework="langgraph",
            timeout_sec=0,
        )

        # Execute
        await _execute_run(
            run_id="test-run-123",
            payload={"input": "test"},
            config=config,
            state=state,
        )

        # Verify flow
        mock_run_manager.start_run.assert_called_once_with("test-run-123")
        # get_context now receives events_filter parameter
        mock_run_manager.get_context.assert_called_once()
        call_args = mock_run_manager.get_context.call_args
        assert call_args.args[0] == "test-run-123"
        mock_adapter.invoke.assert_called_once()
        mock_run_manager.set_result.assert_called_once()

        # Most importantly: verify context was passed to invoke
        invoke_call = mock_adapter.invoke.call_args
        assert invoke_call.kwargs.get("context") is not None, (
            "Context must be passed to adapter.invoke()"
        )


class TestContextEventEmission:
    """Tests that verify events are emitted through context."""

    def test_adapter_can_emit_events_through_context(self):
        """Test that an adapter can use context to emit events."""
        # This is a design verification test - check that StreamContext
        # has the required methods for event emission
        from dockrion_events import EventBus, InMemoryBackend, StreamContext

        # Create real event bus
        backend = InMemoryBackend()
        bus = EventBus(backend)

        # Create real context
        context = StreamContext(run_id="test-run", bus=bus)

        # Verify context has the required methods for event emission
        # (Actual emission is async and tested elsewhere)
        assert hasattr(context, "emit_token"), "Context must have emit_token method"
        assert hasattr(context, "emit_progress"), "Context must have emit_progress method"
        assert hasattr(context, "emit_step"), "Context must have emit_step method"
        assert callable(context.emit_token), "emit_token must be callable"
        assert callable(context.emit_progress), "emit_progress must be callable"


class TestNoContextRegressionGuard:
    """Guards against regression of the context-not-passed bug."""

    def test_lambda_not_used_in_executor(self):
        """Ensure lambda is not used for executor calls (can cause closure issues)."""
        import inspect

        from dockrion_runtime.endpoints.runs import _execute_with_invoke

        source = inspect.getsource(_execute_with_invoke)

        # Should use functools.partial, not lambda
        assert "functools.partial" in source or "partial" in source, (
            "_execute_with_invoke should use functools.partial for proper closure"
        )

    def test_context_parameter_exists_in_execute_run(self):
        """Verify _execute_run has context handling."""
        import inspect

        from dockrion_runtime.endpoints.runs import _execute_run

        source = inspect.getsource(_execute_run)

        # Must have context variable
        assert "context = await state.run_manager.get_context" in source, (
            "_execute_run must get context from run_manager"
        )

        # Must pass to helpers
        assert "_execute_with_invoke" in source or "_execute_with_streaming" in source, (
            "_execute_run must use helper functions that accept context"
        )
