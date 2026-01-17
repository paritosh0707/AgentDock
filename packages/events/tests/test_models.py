"""Tests for event models."""

from datetime import datetime, timezone

import pytest


class TestBaseEvent:
    """Tests for BaseEvent and event creation."""

    def test_base_event_auto_generates_id(self):
        """Base event should auto-generate an ID."""
        from dockrion_events import BaseEvent

        event = BaseEvent(type="test", run_id="run-123", sequence=1)
        assert event.id is not None
        assert event.id.startswith("evt-")

    def test_base_event_auto_generates_timestamp(self):
        """Base event should auto-generate a timestamp."""
        from dockrion_events import BaseEvent

        event = BaseEvent(type="test", run_id="run-123", sequence=1)
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

    def test_base_event_to_dict(self):
        """Base event should serialize to dict."""
        from dockrion_events import BaseEvent

        event = BaseEvent(type="test", run_id="run-123", sequence=1)
        data = event.to_dict()

        assert data["type"] == "test"
        assert data["run_id"] == "run-123"
        assert data["sequence"] == 1
        assert "id" in data
        assert "timestamp" in data

    def test_base_event_to_sse(self):
        """Base event should format for SSE."""
        from dockrion_events import BaseEvent

        event = BaseEvent(type="test", run_id="run-123", sequence=1)
        sse = event.to_sse()

        assert sse.startswith("event: test\n")
        assert "data: " in sse
        assert sse.endswith("\n\n")


class TestProgressEvent:
    """Tests for ProgressEvent."""

    def test_progress_event_creation(self):
        """Progress event should be created with required fields."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(
            run_id="run-123",
            sequence=1,
            step="parsing",
            progress=0.5,
            message="Parsing document...",
        )

        assert event.type == "progress"
        assert event.step == "parsing"
        assert event.progress == 0.5
        assert event.message == "Parsing document..."

    def test_progress_event_clamps_progress(self):
        """Progress should be clamped between 0.0 and 1.0."""
        from dockrion_events import ProgressEvent

        event_low = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=-0.5)
        assert event_low.progress == 0.0

        event_high = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=1.5)
        assert event_high.progress == 1.0


class TestCheckpointEvent:
    """Tests for CheckpointEvent."""

    def test_checkpoint_event_creation(self):
        """Checkpoint event should be created with data."""
        from dockrion_events import CheckpointEvent

        event = CheckpointEvent(
            run_id="run-123",
            sequence=2,
            name="parsed_document",
            data={"fields": 15, "confidence": 0.9},
        )

        assert event.type == "checkpoint"
        assert event.name == "parsed_document"
        assert event.data == {"fields": 15, "confidence": 0.9}


class TestTokenEvent:
    """Tests for TokenEvent."""

    def test_token_event_creation(self):
        """Token event should be created with content."""
        from dockrion_events import TokenEvent

        event = TokenEvent(
            run_id="run-123",
            sequence=3,
            content="Hello",
        )

        assert event.type == "token"
        assert event.content == "Hello"
        assert event.finish_reason is None

    def test_token_event_with_finish_reason(self):
        """Token event should accept finish_reason."""
        from dockrion_events import TokenEvent

        event = TokenEvent(
            run_id="run-123",
            sequence=4,
            content=" world!",
            finish_reason="stop",
        )

        assert event.finish_reason == "stop"


class TestStepEvent:
    """Tests for StepEvent."""

    def test_step_event_creation(self):
        """Step event should be created with node_name."""
        from dockrion_events import StepEvent

        event = StepEvent(
            run_id="run-123",
            sequence=5,
            node_name="extract_fields",
            duration_ms=150,
            input_keys=["document"],
            output_keys=["extracted_fields"],
        )

        assert event.type == "step"
        assert event.node_name == "extract_fields"
        assert event.duration_ms == 150
        assert event.input_keys == ["document"]
        assert event.output_keys == ["extracted_fields"]


class TestCompleteEvent:
    """Tests for CompleteEvent."""

    def test_complete_event_creation(self):
        """Complete event should be created with output."""
        from dockrion_events import CompleteEvent

        event = CompleteEvent(
            run_id="run-123",
            sequence=10,
            output={"result": "done"},
            latency_seconds=2.5,
            metadata={"agent": "test-agent"},
        )

        assert event.type == "complete"
        assert event.output == {"result": "done"}
        assert event.latency_seconds == 2.5
        assert event.metadata == {"agent": "test-agent"}


class TestErrorEvent:
    """Tests for ErrorEvent."""

    def test_error_event_creation(self):
        """Error event should be created with error message."""
        from dockrion_events import ErrorEvent

        event = ErrorEvent(
            run_id="run-123",
            sequence=10,
            error="Something went wrong",
            code="INTERNAL_ERROR",
            details={"line": 42},
        )

        assert event.type == "error"
        assert event.error == "Something went wrong"
        assert event.code == "INTERNAL_ERROR"
        assert event.details == {"line": 42}


class TestParseEvent:
    """Tests for event parsing."""

    def test_parse_event_progress(self):
        """Should parse progress event from dict."""
        from dockrion_events.models import parse_event

        data = {
            "id": "evt-123",
            "type": "progress",
            "run_id": "run-123",
            "sequence": 1,
            "timestamp": "2024-01-15T10:30:00Z",
            "step": "parsing",
            "progress": 0.5,
        }

        event = parse_event(data)
        assert event.type == "progress"
        assert event.step == "parsing"

    def test_parse_event_complete(self):
        """Should parse complete event from dict."""
        from dockrion_events.models import parse_event

        data = {
            "id": "evt-456",
            "type": "complete",
            "run_id": "run-123",
            "sequence": 10,
            "timestamp": "2024-01-15T10:30:05Z",
            "output": {"result": "done"},
        }

        event = parse_event(data)
        assert event.type == "complete"
        assert event.output == {"result": "done"}

    def test_parse_event_unknown_type(self):
        """Should parse unknown event type as BaseEvent."""
        from dockrion_events.models import BaseEvent, parse_event

        data = {
            "type": "custom_event",
            "run_id": "run-123",
            "sequence": 1,
            "custom_field": "value",
        }

        event = parse_event(data)
        assert isinstance(event, BaseEvent)
        assert event.type == "custom_event"

    def test_parse_event_missing_type(self):
        """Should raise error for missing type."""
        from dockrion_events.models import parse_event

        data = {"run_id": "run-123", "sequence": 1}

        with pytest.raises(ValueError, match="missing 'type' field"):
            parse_event(data)


class TestTerminalEvents:
    """Tests for terminal event detection."""

    def test_is_terminal_event_complete(self):
        """Complete event should be terminal."""
        from dockrion_events import CompleteEvent
        from dockrion_events.models import is_terminal_event

        event = CompleteEvent(run_id="run-123", sequence=10, output={})
        assert is_terminal_event(event) is True

    def test_is_terminal_event_error(self):
        """Error event should be terminal."""
        from dockrion_events import ErrorEvent
        from dockrion_events.models import is_terminal_event

        event = ErrorEvent(run_id="run-123", sequence=10, error="fail")
        assert is_terminal_event(event) is True

    def test_is_terminal_event_cancelled(self):
        """Cancelled event should be terminal."""
        from dockrion_events import CancelledEvent
        from dockrion_events.models import is_terminal_event

        event = CancelledEvent(run_id="run-123", sequence=10)
        assert is_terminal_event(event) is True

    def test_is_terminal_event_progress(self):
        """Progress event should not be terminal."""
        from dockrion_events import ProgressEvent
        from dockrion_events.models import is_terminal_event

        event = ProgressEvent(run_id="run-123", sequence=5, step="test", progress=0.5)
        assert is_terminal_event(event) is False
