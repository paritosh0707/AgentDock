"""Tests for StreamContext."""

import asyncio

import pytest


class TestStreamContext:
    """Tests for StreamContext."""

    @pytest.mark.asyncio
    async def test_run_id_property(self, stream_context, sample_run_id):
        """Should expose run_id property."""
        assert stream_context.run_id == sample_run_id

    @pytest.mark.asyncio
    async def test_emit_progress(self, stream_context, event_bus, sample_run_id):
        """Should emit progress event."""
        event = await stream_context.emit_progress(
            step="parsing", progress=0.5, message="Parsing..."
        )

        assert event.type == "progress"
        assert event.step == "parsing"
        assert event.progress == 0.5
        assert event.message == "Parsing..."
        assert event.sequence == 1

        # Verify event was stored
        events = await event_bus.get_events(sample_run_id)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_checkpoint(self, stream_context, event_bus, sample_run_id):
        """Should emit checkpoint event."""
        event = await stream_context.checkpoint(
            name="parsed_doc", data={"fields": 15, "confidence": 0.9}
        )

        assert event.type == "checkpoint"
        assert event.name == "parsed_doc"
        assert event.data == {"fields": 15, "confidence": 0.9}

    @pytest.mark.asyncio
    async def test_emit_token(self, stream_context):
        """Should emit token event."""
        event = await stream_context.emit_token(content="Hello")
        assert event.type == "token"
        assert event.content == "Hello"
        assert event.finish_reason is None

        event2 = await stream_context.emit_token(content=" world!", finish_reason="stop")
        assert event2.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_emit_step(self, stream_context):
        """Should emit step event."""
        event = await stream_context.emit_step(
            node_name="extract_fields",
            duration_ms=150,
            input_keys=["doc"],
            output_keys=["fields"],
        )

        assert event.type == "step"
        assert event.node_name == "extract_fields"
        assert event.duration_ms == 150
        assert event.input_keys == ["doc"]
        assert event.output_keys == ["fields"]

    @pytest.mark.asyncio
    async def test_emit_complete(self, stream_context):
        """Should emit complete event."""
        event = await stream_context.emit_complete(
            output={"result": "done"},
            latency_seconds=2.5,
            metadata={"agent": "test"},
        )

        assert event.type == "complete"
        assert event.output == {"result": "done"}
        assert event.latency_seconds == 2.5

    @pytest.mark.asyncio
    async def test_emit_error(self, stream_context):
        """Should emit error event."""
        event = await stream_context.emit_error(
            error="Something went wrong",
            code="TEST_ERROR",
            details={"line": 42},
        )

        assert event.type == "error"
        assert event.error == "Something went wrong"
        assert event.code == "TEST_ERROR"

    @pytest.mark.asyncio
    async def test_emit_custom(self, stream_context):
        """Should emit custom event."""
        event = await stream_context.emit(
            event_type="fraud_check",
            data={"passed": True, "score": 0.02},
        )

        assert event.type == "fraud_check"

    @pytest.mark.asyncio
    async def test_sequence_numbering(self, stream_context):
        """Should auto-increment sequence numbers."""
        event1 = await stream_context.emit_progress("step1", 0.1)
        event2 = await stream_context.emit_progress("step2", 0.2)
        event3 = await stream_context.emit_progress("step3", 0.3)

        assert event1.sequence == 1
        assert event2.sequence == 2
        assert event3.sequence == 3

    @pytest.mark.asyncio
    async def test_emit_started(self, stream_context):
        """Should emit started event."""
        event = await stream_context.emit_started(agent_name="test-agent", framework="custom")

        assert event.type == "started"
        assert event.agent_name == "test-agent"
        assert event.framework == "custom"

    @pytest.mark.asyncio
    async def test_emit_heartbeat(self, stream_context):
        """Should emit heartbeat event."""
        event = await stream_context.emit_heartbeat()
        assert event.type == "heartbeat"

    @pytest.mark.asyncio
    async def test_emit_cancelled(self, stream_context):
        """Should emit cancelled event."""
        event = await stream_context.emit_cancelled(reason="User requested")
        assert event.type == "cancelled"
        assert event.reason == "User requested"


class TestContextAccess:
    """Tests for thread-local context access."""

    def test_get_current_context_default(self):
        """Should return None when no context is set."""
        from dockrion_events import get_current_context

        assert get_current_context() is None

    def test_set_and_get_current_context(self, stream_context):
        """Should set and get current context."""
        from dockrion_events import get_current_context, set_current_context

        set_current_context(stream_context)
        assert get_current_context() is stream_context

        set_current_context(None)
        assert get_current_context() is None

    def test_context_scope(self, stream_context):
        """Should set context within scope and restore after."""
        from dockrion_events import context_scope, get_current_context

        assert get_current_context() is None

        with context_scope(stream_context):
            assert get_current_context() is stream_context

        assert get_current_context() is None

    def test_nested_context_scope(self, event_bus, sample_run_id):
        """Should handle nested context scopes."""
        from dockrion_events import StreamContext, context_scope, get_current_context

        context1 = StreamContext(run_id="run-1", bus=event_bus)
        context2 = StreamContext(run_id="run-2", bus=event_bus)

        with context_scope(context1):
            assert get_current_context().run_id == "run-1"

            with context_scope(context2):
                assert get_current_context().run_id == "run-2"

            assert get_current_context().run_id == "run-1"

        assert get_current_context() is None


class TestSyncEmitMethods:
    """Tests for synchronous emit methods."""

    def test_sync_emit_progress(self, stream_context):
        """Should emit progress synchronously."""
        # This should not raise
        stream_context.sync_emit_progress("test", 0.5, "Testing...")

    def test_sync_checkpoint(self, stream_context):
        """Should emit checkpoint synchronously."""
        stream_context.sync_checkpoint("test", {"data": "value"})

    def test_sync_emit_token(self, stream_context):
        """Should emit token synchronously."""
        stream_context.sync_emit_token("Hello")

    def test_sync_emit_step(self, stream_context):
        """Should emit step synchronously."""
        stream_context.sync_emit_step("test_node", duration_ms=100)

    def test_sync_emit_custom(self, stream_context):
        """Should emit custom event synchronously."""
        stream_context.sync_emit("custom_type", {"key": "value"})


class TestQueueMode:
    """Tests for queue mode (Pattern A)."""

    def test_queue_mode_creation_without_bus(self):
        """Should create context in queue mode without bus."""
        from dockrion_events import StreamContext

        context = StreamContext(run_id="test-123", queue_mode=True)
        assert context.queue_mode is True
        assert context.run_id == "test-123"

    def test_queue_mode_requires_no_bus(self):
        """Queue mode should not require EventBus."""
        from dockrion_events import StreamContext

        # Should not raise
        context = StreamContext(run_id="test-123", queue_mode=True)
        assert context is not None

    def test_non_queue_mode_requires_bus(self):
        """Non-queue mode should require EventBus."""
        from dockrion_events import StreamContext

        with pytest.raises(ValueError) as exc_info:
            StreamContext(run_id="test-123", queue_mode=False)

        assert "EventBus required" in str(exc_info.value)

    def test_sync_emit_queues_events(self):
        """Sync emit in queue mode should queue events."""
        from dockrion_events import StreamContext

        context = StreamContext(run_id="test-123", queue_mode=True)

        context.sync_emit_token("Hello")
        context.sync_emit_token(" world")

        assert context.has_queued_events()
        assert context.queue_size() == 2

    def test_drain_queued_events(self):
        """Should drain all queued events in order."""
        from dockrion_events import StreamContext

        context = StreamContext(run_id="test-123", queue_mode=True)

        context.sync_emit_token("Hello")
        context.sync_emit_step("node1")
        context.sync_emit_token(" world")

        events = context.drain_queued_events()

        assert len(events) == 3
        assert events[0].type == "token"
        assert events[0].content == "Hello"
        assert events[1].type == "step"
        assert events[2].type == "token"

    def test_drain_clears_queue(self):
        """Drain should clear the queue."""
        from dockrion_events import StreamContext

        context = StreamContext(run_id="test-123", queue_mode=True)

        context.sync_emit_token("Hello")
        events1 = context.drain_queued_events()
        events2 = context.drain_queued_events()

        assert len(events1) == 1
        assert len(events2) == 0
        assert not context.has_queued_events()

    def test_queue_mode_with_filter(self):
        """Queue mode should work with events filter."""
        from dockrion_events import EventsFilter, StreamContext

        filter = EventsFilter(["token"])
        context = StreamContext(run_id="test-123", queue_mode=True, events_filter=filter)

        context.sync_emit_token("Hello")  # Should be queued
        context.sync_emit_step("node1")  # Should be filtered out

        events = context.drain_queued_events()
        assert len(events) == 1
        assert events[0].type == "token"


class TestEventsFiltering:
    """Tests for events filtering in StreamContext."""

    def test_filter_denies_progress(self):
        """Progress should be filtered when not allowed."""
        from dockrion_events import EventsFilter, StreamContext

        filter = EventsFilter(["token", "step"])  # No progress
        context = StreamContext(run_id="test-123", queue_mode=True, events_filter=filter)

        # Progress should be filtered out (returns False)
        result = context.sync_emit_progress("test", 0.5)
        assert result is False

        events = context.drain_queued_events()
        assert len(events) == 0

    def test_filter_allows_token(self):
        """Token should be allowed when in filter."""
        from dockrion_events import EventsFilter, StreamContext

        filter = EventsFilter(["token"])
        context = StreamContext(run_id="test-123", queue_mode=True, events_filter=filter)

        result = context.sync_emit_token("Hello")
        assert result is True

        events = context.drain_queued_events()
        assert len(events) == 1

    def test_filter_denies_custom_event(self):
        """Custom events should be filtered correctly."""
        from dockrion_events import EventsFilter, StreamContext

        filter = EventsFilter(["token", "custom:allowed_event"])
        context = StreamContext(run_id="test-123", queue_mode=True, events_filter=filter)

        # Allowed custom event
        result1 = context.sync_emit("allowed_event", {"data": "value"})
        assert result1 is True

        # Denied custom event
        result2 = context.sync_emit("other_event", {"data": "value"})
        assert result2 is False

        events = context.drain_queued_events()
        assert len(events) == 1

    def test_no_filter_allows_all(self):
        """No filter should allow all events."""
        from dockrion_events import StreamContext

        context = StreamContext(run_id="test-123", queue_mode=True, events_filter=None)

        context.sync_emit_token("Hello")
        context.sync_emit_step("node1")
        context.sync_emit_progress("test", 0.5)
        context.sync_emit("custom_event", {"data": "value"})

        events = context.drain_queued_events()
        assert len(events) == 4

    @pytest.mark.asyncio
    async def test_async_emit_with_filter(self):
        """Async emit should also respect filter."""
        from dockrion_events import EventsFilter, StreamContext

        filter = EventsFilter(["token"])
        context = StreamContext(run_id="test-123", queue_mode=True, events_filter=filter)

        # Token should be allowed
        event = await context.emit_token("Hello")
        assert event is not None

        # Progress should be filtered
        event2 = await context.emit_progress("test", 0.5)
        assert event2 is None

    def test_filter_property(self):
        """Should expose events_filter property."""
        from dockrion_events import EventsFilter, StreamContext

        filter = EventsFilter(["token"])
        context = StreamContext(run_id="test-123", queue_mode=True, events_filter=filter)

        assert context.events_filter is filter

    def test_queue_mode_property(self):
        """Should expose queue_mode property."""
        from dockrion_events import StreamContext

        context = StreamContext(run_id="test-123", queue_mode=True)
        assert context.queue_mode is True

        # queue_mode=False requires a bus, so we can't test it without one
        # Just verify the queue_mode property returns True for queue mode context
        assert context.queue_mode is True


class TestSyncHeartbeat:
    """Test sync heartbeat method."""

    def test_sync_emit_heartbeat(self):
        """Should emit heartbeat synchronously."""
        from dockrion_events import StreamContext

        context = StreamContext(run_id="test-123", queue_mode=True)
        result = context.sync_emit_heartbeat()
        assert result is True

        events = context.drain_queued_events()
        assert len(events) == 1
        assert events[0].type == "heartbeat"

    def test_sync_emit_heartbeat_filtered(self):
        """Heartbeat should be filterable."""
        from dockrion_events import EventsFilter, StreamContext

        filter = EventsFilter(["token"])  # No heartbeat
        context = StreamContext(run_id="test-123", queue_mode=True, events_filter=filter)

        result = context.sync_emit_heartbeat()
        assert result is False

        events = context.drain_queued_events()
        assert len(events) == 0
