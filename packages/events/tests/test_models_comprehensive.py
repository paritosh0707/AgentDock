"""Comprehensive tests for event models.

These tests ensure type safety, immutability, validation, and proper behavior
across all event types and edge cases.
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


class TestEventTypeImmutability:
    """Test that event type fields are immutable."""

    def test_started_event_type_is_frozen(self):
        """Type field should be frozen and cannot be changed."""
        from dockrion_events import StartedEvent

        event = StartedEvent(run_id="run-123", sequence=1)
        assert event.type == "started"

        # Attempting to change type should fail
        with pytest.raises((ValidationError, AttributeError)):
            event.type = "different"  # type: ignore[misc]

    def test_progress_event_type_is_frozen(self):
        """Type field should be frozen and cannot be changed."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=0.5)
        assert event.type == "progress"

        with pytest.raises((ValidationError, AttributeError)):
            event.type = "different"  # type: ignore[misc]

    def test_complete_event_type_is_frozen(self):
        """Type field should be frozen and cannot be changed."""
        from dockrion_events import CompleteEvent

        event = CompleteEvent(run_id="run-123", sequence=1, output={})
        assert event.type == "complete"

        with pytest.raises((ValidationError, AttributeError)):
            event.type = "different"  # type: ignore[misc]


class TestEventSerialization:
    """Test event serialization and deserialization."""

    def test_progress_event_round_trip(self):
        """Event should serialize and deserialize correctly."""
        from dockrion_events.models import ProgressEvent, parse_event

        original = ProgressEvent(
            run_id="run-123",
            sequence=5,
            step="parsing",
            progress=0.75,
            message="Almost done",
        )

        # Serialize to dict
        data = original.to_dict()
        assert data["type"] == "progress"
        assert data["run_id"] == "run-123"
        assert data["sequence"] == 5
        assert data["step"] == "parsing"
        assert data["progress"] == 0.75

        # Deserialize back
        parsed = parse_event(data)
        assert isinstance(parsed, ProgressEvent)
        assert parsed.type == "progress"
        assert parsed.run_id == "run-123"
        assert parsed.sequence == 5
        assert parsed.step == "parsing"
        assert parsed.progress == 0.75

    def test_checkpoint_event_round_trip(self):
        """Checkpoint event with complex data should serialize correctly."""
        from dockrion_events.models import CheckpointEvent, parse_event

        original = CheckpointEvent(
            run_id="run-123",
            sequence=3,
            name="intermediate",
            data={"nested": {"value": 42}, "list": [1, 2, 3]},
        )

        data = original.to_dict()
        parsed = parse_event(data)

        assert isinstance(parsed, CheckpointEvent)
        assert parsed.data == {"nested": {"value": 42}, "list": [1, 2, 3]}

    def test_sse_format(self):
        """Event SSE format should be valid."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=0.5)
        sse = event.to_sse()

        assert sse.startswith("event: progress\n")
        assert "data: " in sse
        assert sse.endswith("\n\n")

        # Should contain JSON data
        data_line = sse.split("data: ")[1].split("\n")[0]
        parsed = json.loads(data_line)
        assert parsed["type"] == "progress"

    def test_json_serialization(self):
        """Event should be JSON serializable."""
        from dockrion_events import CompleteEvent

        event = CompleteEvent(
            run_id="run-123",
            sequence=10,
            output={"result": "success", "count": 42},
            latency_seconds=2.5,
        )

        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "complete"
        assert parsed["output"]["count"] == 42


class TestEventValidation:
    """Test field validation rules."""

    def test_progress_clamping_negative(self):
        """Negative progress should clamp to 0.0."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=-0.5)
        assert event.progress == 0.0

    def test_progress_clamping_over_one(self):
        """Progress > 1.0 should clamp to 1.0."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=1.5)
        assert event.progress == 1.0

    def test_progress_clamping_at_boundaries(self):
        """Boundary values should be valid."""
        from dockrion_events import ProgressEvent

        event_zero = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=0.0)
        assert event_zero.progress == 0.0

        event_one = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=1.0)
        assert event_one.progress == 1.0

    def test_required_fields_validation(self):
        """Missing required fields should raise ValidationError."""
        from dockrion_events import ProgressEvent

        # Missing run_id
        with pytest.raises(ValidationError):
            ProgressEvent(sequence=1, step="test", progress=0.5)  # type: ignore[call-arg]

        # Missing step
        with pytest.raises(ValidationError):
            ProgressEvent(run_id="run-123", sequence=1, progress=0.5)  # type: ignore[call-arg]

    def test_optional_fields(self):
        """Optional fields should work with None."""
        from dockrion_events import StartedEvent

        event = StartedEvent(run_id="run-123", sequence=1)
        assert event.agent_name is None
        assert event.framework is None

        event_with_values = StartedEvent(
            run_id="run-123", sequence=1, agent_name="my-agent", framework="langgraph"
        )
        assert event_with_values.agent_name == "my-agent"
        assert event_with_values.framework == "langgraph"


class TestEventDefaults:
    """Test default value generation."""

    def test_id_auto_generation(self):
        """ID should be auto-generated if not provided."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=0.5)
        assert event.id is not None
        assert event.id.startswith("evt-")
        assert len(event.id) == 16  # evt- + 12 hex chars

    def test_timestamp_auto_generation(self):
        """Timestamp should be auto-generated if not provided."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=0.5)
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == timezone.utc

    def test_unique_ids(self):
        """Each event should get a unique ID."""
        from dockrion_events import ProgressEvent

        event1 = ProgressEvent(run_id="run-123", sequence=1, step="test", progress=0.5)
        event2 = ProgressEvent(run_id="run-123", sequence=2, step="test", progress=0.6)

        assert event1.id != event2.id

    def test_default_empty_dicts(self):
        """Dict fields should default to empty dicts."""
        from dockrion_events import CheckpointEvent, CompleteEvent

        checkpoint = CheckpointEvent(run_id="run-123", sequence=1, name="test")
        assert checkpoint.data == {}

        complete = CompleteEvent(run_id="run-123", sequence=10)
        assert complete.output == {}
        assert complete.metadata == {}

    def test_default_empty_lists(self):
        """List fields should default to empty lists."""
        from dockrion_events import StepEvent

        step = StepEvent(run_id="run-123", sequence=5, node_name="test_node")
        assert step.input_keys == []
        assert step.output_keys == []


class TestEventFactory:
    """Test create_event factory function."""

    def test_create_progress_event(self):
        """Factory should create ProgressEvent."""
        from dockrion_events.models import ProgressEvent, create_event

        event = create_event("progress", "run-123", 5, step="parsing", progress=0.5)
        assert isinstance(event, ProgressEvent)
        assert event.type == "progress"
        assert event.run_id == "run-123"
        assert event.sequence == 5
        assert event.step == "parsing"

    def test_create_complete_event(self):
        """Factory should create CompleteEvent."""
        from dockrion_events.models import CompleteEvent, create_event

        event = create_event("complete", "run-123", 10, output={"result": "done"})
        assert isinstance(event, CompleteEvent)
        assert event.type == "complete"
        assert event.output == {"result": "done"}

    def test_create_unknown_event_type(self):
        """Factory should create BaseEvent for unknown types."""
        from dockrion_events.models import BaseEvent, create_event

        event = create_event("custom_event", "run-123", 1, custom_field="value")
        assert isinstance(event, BaseEvent)
        assert event.type == "custom_event"


class TestTerminalEventDetection:
    """Test terminal event detection."""

    def test_complete_is_terminal(self):
        """CompleteEvent should be detected as terminal."""
        from dockrion_events import CompleteEvent
        from dockrion_events.models import is_terminal_event

        event = CompleteEvent(run_id="run-123", sequence=10, output={})
        assert is_terminal_event(event) is True

    def test_error_is_terminal(self):
        """ErrorEvent should be detected as terminal."""
        from dockrion_events import ErrorEvent
        from dockrion_events.models import is_terminal_event

        event = ErrorEvent(run_id="run-123", sequence=10, error="Failed")
        assert is_terminal_event(event) is True

    def test_cancelled_is_terminal(self):
        """CancelledEvent should be detected as terminal."""
        from dockrion_events import CancelledEvent
        from dockrion_events.models import is_terminal_event

        event = CancelledEvent(run_id="run-123", sequence=10)
        assert is_terminal_event(event) is True

    def test_progress_not_terminal(self):
        """ProgressEvent should not be terminal."""
        from dockrion_events import ProgressEvent
        from dockrion_events.models import is_terminal_event

        event = ProgressEvent(run_id="run-123", sequence=5, step="test", progress=0.5)
        assert is_terminal_event(event) is False

    def test_started_not_terminal(self):
        """StartedEvent should not be terminal."""
        from dockrion_events import StartedEvent
        from dockrion_events.models import is_terminal_event

        event = StartedEvent(run_id="run-123", sequence=1)
        assert is_terminal_event(event) is False


class TestAllEventTypes:
    """Test creation of all event types."""

    def test_started_event(self):
        """StartedEvent should create correctly."""
        from dockrion_events import StartedEvent

        event = StartedEvent(
            run_id="run-123", sequence=1, agent_name="test-agent", framework="custom"
        )
        assert event.type == "started"
        assert event.agent_name == "test-agent"
        assert event.framework == "custom"

    def test_progress_event(self):
        """ProgressEvent should create correctly."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(
            run_id="run-123", sequence=2, step="parsing", progress=0.5, message="Halfway"
        )
        assert event.type == "progress"
        assert event.step == "parsing"
        assert event.progress == 0.5

    def test_checkpoint_event(self):
        """CheckpointEvent should create correctly."""
        from dockrion_events import CheckpointEvent

        event = CheckpointEvent(
            run_id="run-123", sequence=3, name="saved_state", data={"key": "value"}
        )
        assert event.type == "checkpoint"
        assert event.name == "saved_state"

    def test_token_event(self):
        """TokenEvent should create correctly."""
        from dockrion_events import TokenEvent

        event = TokenEvent(
            run_id="run-123", sequence=4, content="Hello", finish_reason="stop"
        )
        assert event.type == "token"
        assert event.content == "Hello"
        assert event.finish_reason == "stop"

    def test_step_event(self):
        """StepEvent should create correctly."""
        from dockrion_events import StepEvent

        event = StepEvent(
            run_id="run-123",
            sequence=5,
            node_name="process_node",
            duration_ms=150,
            input_keys=["input"],
            output_keys=["output"],
        )
        assert event.type == "step"
        assert event.node_name == "process_node"
        assert event.duration_ms == 150

    def test_complete_event(self):
        """CompleteEvent should create correctly."""
        from dockrion_events import CompleteEvent

        event = CompleteEvent(
            run_id="run-123",
            sequence=10,
            output={"result": "done"},
            latency_seconds=2.5,
            metadata={"agent": "test"},
        )
        assert event.type == "complete"
        assert event.output == {"result": "done"}
        assert event.latency_seconds == 2.5

    def test_error_event(self):
        """ErrorEvent should create correctly."""
        from dockrion_events import ErrorEvent

        event = ErrorEvent(
            run_id="run-123",
            sequence=10,
            error="Something failed",
            code="TEST_ERROR",
            details={"line": 42},
        )
        assert event.type == "error"
        assert event.error == "Something failed"
        assert event.code == "TEST_ERROR"

    def test_heartbeat_event(self):
        """HeartbeatEvent should create correctly."""
        from dockrion_events import HeartbeatEvent

        event = HeartbeatEvent(run_id="run-123", sequence=7)
        assert event.type == "heartbeat"

    def test_cancelled_event(self):
        """CancelledEvent should create correctly."""
        from dockrion_events import CancelledEvent

        event = CancelledEvent(run_id="run-123", sequence=10, reason="User cancelled")
        assert event.type == "cancelled"
        assert event.reason == "User cancelled"


class TestParseEventErrors:
    """Test parse_event error handling."""

    def test_parse_event_missing_type(self):
        """parse_event should raise for missing type."""
        from dockrion_events.models import parse_event

        with pytest.raises(ValueError, match="missing 'type' field"):
            parse_event({"run_id": "run-123", "sequence": 1})

    def test_parse_event_invalid_data(self):
        """parse_event should raise for invalid event data."""
        from dockrion_events.models import parse_event

        # Missing required fields for progress event
        with pytest.raises(ValidationError):
            parse_event({"type": "progress", "run_id": "run-123", "sequence": 1})

    def test_parse_custom_event_with_base_model(self):
        """parse_event should use BaseEvent for unknown types."""
        from dockrion_events.models import BaseEvent, parse_event

        event = parse_event(
            {
                "type": "custom_type",
                "run_id": "run-123",
                "sequence": 1,
                "custom_field": "value",
            }
        )
        assert isinstance(event, BaseEvent)
        assert event.type == "custom_type"


class TestEventEquality:
    """Test event comparison and hashing."""

    def test_events_with_same_data_are_equal(self):
        """Events with same data should compare equal."""
        from dockrion_events import ProgressEvent

        event1 = ProgressEvent(
            id="evt-123",
            run_id="run-123",
            sequence=1,
            step="test",
            progress=0.5,
        )
        event2 = ProgressEvent(
            id="evt-123",
            run_id="run-123",
            sequence=1,
            step="test",
            progress=0.5,
        )

        assert event1.id == event2.id
        assert event1.run_id == event2.run_id

    def test_events_with_different_ids_differ(self):
        """Events with different IDs should not be equal."""
        from dockrion_events import ProgressEvent

        event1 = ProgressEvent(
            id="evt-123",
            run_id="run-123",
            sequence=1,
            step="test",
            progress=0.5,
        )
        event2 = ProgressEvent(
            id="evt-456",
            run_id="run-123",
            sequence=1,
            step="test",
            progress=0.5,
        )

        assert event1.id != event2.id
