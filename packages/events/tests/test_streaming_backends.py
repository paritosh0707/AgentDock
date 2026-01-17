"""
Tests for streaming backends (LangGraphBackend, QueueBackend).

These backends are used by StreamContext for native framework streaming.
"""

from unittest.mock import MagicMock, patch

import pytest

from dockrion_events import LangGraphBackend, QueueBackend, StreamingBackend
from dockrion_events.models import CheckpointEvent, ProgressEvent, TokenEvent


class TestQueueBackend:
    """Tests for QueueBackend."""

    def test_implements_protocol(self):
        """QueueBackend should implement StreamingBackend protocol."""
        backend = QueueBackend()
        assert isinstance(backend, StreamingBackend)

    def test_name_property(self):
        """Should return 'queue' as name."""
        backend = QueueBackend()
        assert backend.name == "queue"

    def test_is_available(self):
        """Queue backend should always be available."""
        backend = QueueBackend()
        assert backend.is_available() is True

    def test_emit_queues_event(self):
        """emit() should add event to queue."""
        backend = QueueBackend()
        event = ProgressEvent(
            run_id="test-123",
            sequence=1,
            step="processing",
            progress=0.5,
        )

        result = backend.emit(event)

        assert result is True
        assert len(backend) == 1

    def test_drain_returns_and_clears(self):
        """drain() should return events and clear queue."""
        backend = QueueBackend()
        event1 = ProgressEvent(run_id="test", sequence=1, step="a", progress=0.1)
        event2 = ProgressEvent(run_id="test", sequence=2, step="b", progress=0.2)

        backend.emit(event1)
        backend.emit(event2)
        assert len(backend) == 2

        events = backend.drain()

        assert len(events) == 2
        assert events[0] == event1
        assert events[1] == event2
        assert len(backend) == 0

    def test_drain_empty_returns_empty_list(self):
        """drain() on empty queue should return empty list."""
        backend = QueueBackend()
        events = backend.drain()
        assert events == []

    def test_multiple_drains(self):
        """Multiple drains should work correctly."""
        backend = QueueBackend()
        event = ProgressEvent(run_id="test", sequence=1, step="a", progress=0.1)

        backend.emit(event)
        first_drain = backend.drain()
        second_drain = backend.drain()

        assert len(first_drain) == 1
        assert len(second_drain) == 0


class TestLangGraphBackend:
    """Tests for LangGraphBackend."""

    def test_implements_protocol(self):
        """LangGraphBackend should implement StreamingBackend protocol."""
        backend = LangGraphBackend()
        assert isinstance(backend, StreamingBackend)

    def test_name_property(self):
        """Should return 'langgraph' as name."""
        backend = LangGraphBackend()
        assert backend.name == "langgraph"

    def test_is_available_without_writer(self):
        """is_available() should return False when no writer available."""
        backend = LangGraphBackend()
        # Without LangGraph context, writer should be None
        assert backend.is_available() is False

    def test_is_available_with_mock_writer(self):
        """is_available() should return True when writer is available."""
        backend = LangGraphBackend()

        # Mock _get_writer directly
        mock_writer = MagicMock()
        backend._get_writer = MagicMock(return_value=mock_writer)

        assert backend.is_available() is True

    def test_emit_without_writer_returns_false(self):
        """emit() should return False when no writer available."""
        backend = LangGraphBackend()
        event = ProgressEvent(
            run_id="test-123",
            sequence=1,
            step="processing",
            progress=0.5,
        )

        result = backend.emit(event)
        assert result is False

    def test_emit_calls_writer_when_available(self):
        """emit() should call writer with event data when available."""
        backend = LangGraphBackend()
        mock_writer = MagicMock()
        backend._get_writer = MagicMock(return_value=mock_writer)

        event = ProgressEvent(
            run_id="test-123",
            sequence=1,
            step="processing",
            progress=0.5,
            message="Halfway done",
        )

        result = backend.emit(event)

        assert result is True
        mock_writer.assert_called_once()
        call_args = mock_writer.call_args[0][0]
        # Should be (event_type, event_data) tuple
        assert isinstance(call_args, tuple)
        assert len(call_args) == 2
        assert call_args[0] == "progress"  # event type
        assert call_args[1]["step"] == "processing"
        assert call_args[1]["progress"] == 0.5


class TestStreamContextWithBackend:
    """Integration tests for StreamContext with streaming backends."""

    def test_context_with_queue_backend(self):
        """StreamContext should use QueueBackend for fallback."""
        from dockrion_events import StreamContext

        backend = QueueBackend()
        context = StreamContext(
            run_id="test-123",
            queue_mode=True,
            streaming_backend=backend,
        )

        # Emit a progress event
        context.sync_emit_progress("step1", 0.5, "Halfway")

        # Event should be in backend queue (or context queue via fallback)
        # The exact behavior depends on whether backend.emit() succeeds
        # Since QueueBackend always succeeds, events go to backend queue
        events = backend.drain()
        assert len(events) == 1
        assert events[0].step == "step1"

    def test_context_falls_back_to_queue_when_backend_unavailable(self):
        """StreamContext should fall back to internal queue when backend fails."""
        from dockrion_events import StreamContext

        # LangGraphBackend will fail without LangGraph context
        backend = LangGraphBackend()
        context = StreamContext(
            run_id="test-123",
            queue_mode=True,
            streaming_backend=backend,
        )

        # Emit a progress event - should fall back to internal queue
        context.sync_emit_progress("step1", 0.5, "Halfway")

        # Event should be in context's internal queue
        events = context.drain_queued_events()
        assert len(events) == 1
        assert events[0].step == "step1"
