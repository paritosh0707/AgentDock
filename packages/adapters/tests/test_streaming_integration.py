"""
Tests for adapter streaming integration with EventsFilter.

Tests cover:
- LangGraphAdapter.invoke_stream with events_filter
- Event draining from queue-mode context
- Custom events interleaving
- LangGraph stream output handlers
"""

import queue
from unittest.mock import MagicMock

import pytest

from dockrion_adapters import LangGraphAdapter
from dockrion_adapters.langgraph_adapter import (
    _drain_user_events,
    _process_langgraph_default_stream,
    _process_langgraph_stream_tuple,
    _process_messages_stream,
    _process_updates_stream,
    _process_values_stream,
)


class TestLangGraphAdapterStreamingFilter:
    """Test LangGraphAdapter streaming with EventsFilter."""

    @pytest.fixture
    def langgraph_adapter(self):
        """Create LangGraphAdapter instance."""
        return LangGraphAdapter()

    @pytest.fixture
    def mock_payload(self):
        """Create mock payload."""
        return {"input": "test message"}

    @pytest.fixture
    def events_filter_chat(self):
        """Create chat preset filter."""
        try:
            from dockrion_events import EventsFilter

            return EventsFilter("chat")
        except ImportError:
            pytest.skip("dockrion_events not installed")

    @pytest.fixture
    def events_filter_minimal(self):
        """Create minimal preset filter."""
        try:
            from dockrion_events import EventsFilter

            return EventsFilter("minimal")
        except ImportError:
            pytest.skip("dockrion_events not installed")

    @pytest.fixture
    def events_filter_token_only(self):
        """Create token-only filter."""
        try:
            from dockrion_events import EventsFilter

            return EventsFilter(["token"])
        except ImportError:
            pytest.skip("dockrion_events not installed")

    def test_invoke_stream_accepts_events_filter(self, langgraph_adapter):
        """invoke_stream should accept events_filter parameter."""
        # Just verify the signature accepts the parameter
        import inspect

        sig = inspect.signature(langgraph_adapter.invoke_stream)
        params = list(sig.parameters.keys())

        assert "events_filter" in params

    def test_filter_determines_stream_modes(self, events_filter_chat):
        """EventsFilter should determine LangGraph stream modes."""
        modes = events_filter_chat.get_langgraph_stream_modes()

        # Chat preset should include messages (token) and updates (step)
        assert "messages" in modes
        assert "updates" in modes

    def test_minimal_filter_returns_values_mode(self, events_filter_minimal):
        """Minimal filter should return values mode only."""
        modes = events_filter_minimal.get_langgraph_stream_modes()

        assert modes == ["values"]

    def test_token_only_filter_returns_messages_mode(self, events_filter_token_only):
        """Token-only filter should return messages mode."""
        modes = events_filter_token_only.get_langgraph_stream_modes()

        assert "messages" in modes
        assert "updates" not in modes


class TestHandlerAdapterStreamingFilter:
    """Test HandlerAdapter streaming with EventsFilter."""

    @pytest.fixture
    def handler_adapter(self):
        """Create HandlerAdapter instance."""
        from dockrion_adapters import HandlerAdapter

        return HandlerAdapter()

    def test_invoke_stream_accepts_events_filter(self, handler_adapter):
        """invoke_stream should accept events_filter parameter."""
        import inspect

        sig = inspect.signature(handler_adapter.invoke_stream)
        params = list(sig.parameters.keys())

        assert "events_filter" in params

    def test_invoke_stream_exists(self, handler_adapter):
        """HandlerAdapter should have invoke_stream method."""
        assert hasattr(handler_adapter, "invoke_stream")
        assert callable(handler_adapter.invoke_stream)


class TestStreamContextQueueModeIntegration:
    """Test StreamContext queue mode in adapter scenarios."""

    @pytest.fixture
    def queue_mode_context(self):
        """Create queue-mode context."""
        try:
            from dockrion_events import EventsFilter, StreamContext

            filter = EventsFilter(["token", "step", "custom"])
            return StreamContext(
                run_id="test-run-123",
                queue_mode=True,
                events_filter=filter,
            )
        except ImportError:
            pytest.skip("dockrion_events not installed")

    def test_context_queues_events_for_draining(self, queue_mode_context):
        """Queue-mode context should queue events for draining."""
        # Emit some events
        queue_mode_context.sync_emit_token("Hello")
        queue_mode_context.sync_emit_step("node1")
        queue_mode_context.sync_emit("custom_event", {"data": "value"})

        # Drain events
        events = queue_mode_context.drain_queued_events()

        assert len(events) == 3
        assert events[0].type == "token"
        assert events[1].type == "step"
        assert events[2].type == "custom_event"

    def test_context_filters_events_before_queuing(self, queue_mode_context):
        """Queue-mode context should filter events."""
        # Progress is not in the filter
        result = queue_mode_context.sync_emit_progress("test", 0.5)
        assert result is False

        # Token is in the filter
        result = queue_mode_context.sync_emit_token("Hello")
        assert result is True

        events = queue_mode_context.drain_queued_events()
        assert len(events) == 1
        assert events[0].type == "token"

    def test_multiple_drain_calls(self, queue_mode_context):
        """Multiple drain calls should return separate event batches."""
        queue_mode_context.sync_emit_token("First")
        events1 = queue_mode_context.drain_queued_events()

        queue_mode_context.sync_emit_token("Second")
        events2 = queue_mode_context.drain_queued_events()

        assert len(events1) == 1
        assert len(events2) == 1
        assert events1[0].content == "First"
        assert events2[0].content == "Second"


class TestEventsFilterPresetBehavior:
    """Test EventsFilter preset behaviors in adapter context."""

    def test_chat_preset_for_ui_streaming(self):
        """Chat preset should be optimized for UI streaming."""
        try:
            from dockrion_events import EventsFilter

            filter = EventsFilter("chat")

            # Chat needs token streaming for real-time output
            assert filter.is_allowed("token")

            # Chat needs step events for progress indication
            assert filter.is_allowed("step")

            # Chat needs heartbeat for connection keep-alive
            assert filter.is_allowed("heartbeat")

            # Chat includes progress for user feedback
            assert filter.is_allowed("progress")

            # Chat doesn't need checkpoint (verbose)
            assert not filter.is_allowed("checkpoint")

        except ImportError:
            pytest.skip("dockrion_events not installed")

    def test_debug_preset_for_development(self):
        """Debug preset should include all events for development."""
        try:
            from dockrion_events import EventsFilter

            filter = EventsFilter("debug")

            # All events should be allowed
            assert filter.is_allowed("token")
            assert filter.is_allowed("step")
            assert filter.is_allowed("progress")
            assert filter.is_allowed("checkpoint")
            assert filter.is_allowed("heartbeat")
            assert filter.is_allowed("custom", "any_event")

        except ImportError:
            pytest.skip("dockrion_events not installed")

    def test_minimal_preset_for_background_jobs(self):
        """Minimal preset should only include lifecycle events."""
        try:
            from dockrion_events import EventsFilter

            filter = EventsFilter("minimal")

            # Only mandatory lifecycle events
            assert filter.is_allowed("started")
            assert filter.is_allowed("complete")
            assert filter.is_allowed("error")
            assert filter.is_allowed("cancelled")

            # No streaming events
            assert not filter.is_allowed("token")
            assert not filter.is_allowed("step")
            assert not filter.is_allowed("progress")

        except ImportError:
            pytest.skip("dockrion_events not installed")


# =============================================================================
# Tests for LangGraph Stream Output Handlers
# =============================================================================


class TestProcessMessagesStream:
    """Test _process_messages_stream helper function."""

    @pytest.fixture
    def result_queue(self):
        """Create a queue for capturing results."""
        return queue.Queue()

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_handles_message_object_with_content(self, result_queue, mock_logger):
        """Should extract content from message object."""
        msg = MagicMock()
        msg.content = "Hello world"

        _process_messages_stream(msg, result_queue, None, True, mock_logger)

        assert not result_queue.empty()
        event = result_queue.get()
        assert event["type"] == "token"
        assert event["content"] == "Hello world"

    def test_handles_tuple_with_message(self, result_queue, mock_logger):
        """Should extract content from (message, metadata) tuple."""
        msg = MagicMock()
        msg.content = "Token content"
        data = (msg, {"some": "metadata"})

        _process_messages_stream(data, result_queue, None, True, mock_logger)

        assert not result_queue.empty()
        event = result_queue.get()
        assert event["type"] == "token"
        assert event["content"] == "Token content"

    def test_handles_string_directly(self, result_queue, mock_logger):
        """Should handle string content directly."""
        _process_messages_stream("Direct string", result_queue, None, True, mock_logger)

        assert not result_queue.empty()
        event = result_queue.get()
        assert event["type"] == "token"
        assert event["content"] == "Direct string"

    def test_handles_dict_with_content_key(self, result_queue, mock_logger):
        """Should extract content from dict with 'content' key."""
        data = {"content": "Dict content", "role": "assistant"}

        _process_messages_stream(data, result_queue, None, True, mock_logger)

        assert not result_queue.empty()
        event = result_queue.get()
        assert event["type"] == "token"
        assert event["content"] == "Dict content"

    def test_respects_emit_tokens_false(self, result_queue, mock_logger):
        """Should not emit when emit_tokens is False."""
        msg = MagicMock()
        msg.content = "Should not appear"

        _process_messages_stream(msg, result_queue, None, False, mock_logger)

        assert result_queue.empty()

    def test_ignores_empty_content(self, result_queue, mock_logger):
        """Should not emit event for empty content."""
        # Use a simple class instead of MagicMock to properly test empty string
        class EmptyMessage:
            content = ""

        msg = EmptyMessage()

        _process_messages_stream(msg, result_queue, None, True, mock_logger)

        assert result_queue.empty()

    def test_emits_through_stream_context(self, result_queue, mock_logger):
        """Should emit through StreamContext if provided."""
        stream_context = MagicMock()
        msg = MagicMock()
        msg.content = "Hello"

        _process_messages_stream(msg, result_queue, stream_context, True, mock_logger)

        stream_context.sync_emit_token.assert_called_once_with("Hello")


class TestProcessUpdatesStream:
    """Test _process_updates_stream helper function."""

    @pytest.fixture
    def result_queue(self):
        """Create a queue for capturing results."""
        return queue.Queue()

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_processes_node_output_dict(self, result_queue, mock_logger):
        """Should process {node_name: output} dict correctly."""
        data = {
            "agent_node": {"messages": ["Hello"], "next": "tool"},
            "tool_node": {"result": "42"},
        }

        _process_updates_stream(data, result_queue, None, True, mock_logger)

        events = []
        while not result_queue.empty():
            events.append(result_queue.get())

        assert len(events) == 2
        assert events[0]["type"] == "step"
        assert events[0]["node"] == "agent_node"
        assert events[1]["type"] == "step"
        assert events[1]["node"] == "tool_node"

    def test_respects_emit_steps_false(self, result_queue, mock_logger):
        """Should not emit when emit_steps is False."""
        data = {"node": {"output": "value"}}

        _process_updates_stream(data, result_queue, None, False, mock_logger)

        assert result_queue.empty()

    def test_emits_through_stream_context(self, result_queue, mock_logger):
        """Should emit step through StreamContext if provided."""
        stream_context = MagicMock()
        data = {"my_node": {"key1": "val1", "key2": "val2"}}

        _process_updates_stream(data, result_queue, stream_context, True, mock_logger)

        stream_context.sync_emit_step.assert_called_once_with(
            node_name="my_node",
            output_keys=["key1", "key2"],
        )

    def test_handles_non_dict_data(self, result_queue, mock_logger):
        """Should handle non-dict data gracefully."""
        _process_updates_stream("not a dict", result_queue, None, True, mock_logger)

        assert result_queue.empty()
        mock_logger.debug.assert_called()


class TestProcessValuesStream:
    """Test _process_values_stream helper function."""

    @pytest.fixture
    def result_queue(self):
        """Create a queue for capturing results."""
        return queue.Queue()

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_emits_state_event(self, result_queue, mock_logger):
        """Should emit state event for values mode."""
        data = {"messages": ["Hello"], "context": {"user": "test"}}

        _process_values_stream(data, result_queue, mock_logger)

        assert not result_queue.empty()
        event = result_queue.get()
        assert event["type"] == "state"
        assert "messages" in event["data"]

    def test_handles_non_dict_data(self, result_queue, mock_logger):
        """Should handle non-dict data gracefully."""
        _process_values_stream("not a dict", result_queue, mock_logger)

        assert result_queue.empty()
        mock_logger.debug.assert_called()


class TestProcessLanggraphStreamTuple:
    """Test _process_langgraph_stream_tuple helper function."""

    @pytest.fixture
    def result_queue(self):
        """Create a queue for capturing results."""
        return queue.Queue()

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_routes_messages_mode(self, result_queue, mock_logger):
        """Should route 'messages' mode to message handler."""
        msg = MagicMock()
        msg.content = "Token"

        _process_langgraph_stream_tuple(
            mode="messages",
            data=msg,
            result_queue=result_queue,
            stream_context=None,
            emit_steps=True,
            emit_tokens=True,
            logger=mock_logger,
        )

        event = result_queue.get()
        assert event["type"] == "token"
        assert event["content"] == "Token"

    def test_routes_updates_mode(self, result_queue, mock_logger):
        """Should route 'updates' mode to updates handler."""
        _process_langgraph_stream_tuple(
            mode="updates",
            data={"my_node": {"output": "value"}},
            result_queue=result_queue,
            stream_context=None,
            emit_steps=True,
            emit_tokens=True,
            logger=mock_logger,
        )

        event = result_queue.get()
        assert event["type"] == "step"
        assert event["node"] == "my_node"

    def test_routes_values_mode(self, result_queue, mock_logger):
        """Should route 'values' mode to values handler."""
        _process_langgraph_stream_tuple(
            mode="values",
            data={"state": "data"},
            result_queue=result_queue,
            stream_context=None,
            emit_steps=True,
            emit_tokens=True,
            logger=mock_logger,
        )

        event = result_queue.get()
        assert event["type"] == "state"

    def test_handles_unknown_mode(self, result_queue, mock_logger):
        """Should log unknown modes."""
        _process_langgraph_stream_tuple(
            mode="unknown_mode",
            data={"some": "data"},
            result_queue=result_queue,
            stream_context=None,
            emit_steps=True,
            emit_tokens=True,
            logger=mock_logger,
        )

        assert result_queue.empty()
        mock_logger.debug.assert_called()


class TestProcessLanggraphDefaultStream:
    """Test _process_langgraph_default_stream helper function."""

    @pytest.fixture
    def result_queue(self):
        """Create a queue for capturing results."""
        return queue.Queue()

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_processes_default_format(self, result_queue, mock_logger):
        """Should process default {node: output} format."""
        step_output = {
            "agent": {"messages": ["Hello"]},
            "tool": {"result": 42},
        }

        _process_langgraph_default_stream(
            step_output, result_queue, None, True, mock_logger
        )

        events = []
        while not result_queue.empty():
            events.append(result_queue.get())

        assert len(events) == 2
        node_names = [e["node"] for e in events]
        assert "agent" in node_names
        assert "tool" in node_names


class TestDrainUserEvents:
    """Test _drain_user_events helper function."""

    @pytest.fixture
    def result_queue(self):
        """Create a queue for capturing results."""
        return queue.Queue()

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_handles_none_context(self, result_queue, mock_logger):
        """Should handle None context gracefully."""
        _drain_user_events(None, result_queue, mock_logger)
        assert result_queue.empty()

    def test_handles_context_without_drain_method(self, result_queue, mock_logger):
        """Should handle context without drain_queued_events method."""
        context = MagicMock(spec=[])  # No methods
        _drain_user_events(context, result_queue, mock_logger)
        assert result_queue.empty()

    def test_drains_events_from_context(self, result_queue, mock_logger):
        """Should drain and queue events from context."""
        event1 = MagicMock()
        event1.type = "custom_event"
        event1.model_dump.return_value = {"data": "value1"}

        event2 = MagicMock()
        event2.type = "another_event"
        event2.model_dump.return_value = {"data": "value2"}

        context = MagicMock()
        context.drain_queued_events.return_value = [event1, event2]

        _drain_user_events(context, result_queue, mock_logger)

        events = []
        while not result_queue.empty():
            events.append(result_queue.get())

        assert len(events) == 2
        assert events[0]["type"] == "custom"
        assert events[0]["event_type"] == "custom_event"
        assert events[1]["event_type"] == "another_event"
