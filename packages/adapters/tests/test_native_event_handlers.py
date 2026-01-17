"""
Tests for native event handlers in LangGraphAdapter.

These handlers process events from LangGraph's "custom" stream mode
when using the native LangGraphBackend.
"""

import queue
from unittest.mock import MagicMock

import pytest

from dockrion_adapters.langgraph_adapter import (
    _NATIVE_EVENT_HANDLERS,
    _process_native_checkpoint,
    _process_native_custom_mode,
    _process_native_progress,
    _process_native_step,
    _process_native_token,
    _process_native_user_custom,
)


class TestNativeProgressHandler:
    """Tests for _process_native_progress."""

    def test_processes_progress_event(self):
        """Should emit correct progress event format."""
        result_queue = queue.Queue()
        event_data = {
            "step": "processing",
            "progress": 0.5,
            "message": "Halfway done",
        }

        _process_native_progress(event_data, result_queue)

        event = result_queue.get_nowait()
        assert event["type"] == "progress"
        assert event["step"] == "processing"
        assert event["progress"] == 0.5
        assert event["message"] == "Halfway done"

    def test_handles_missing_fields(self):
        """Should handle missing optional fields."""
        result_queue = queue.Queue()
        event_data = {}

        _process_native_progress(event_data, result_queue)

        event = result_queue.get_nowait()
        assert event["type"] == "progress"
        assert event["step"] == ""
        assert event["progress"] == 0.0
        assert event["message"] is None


class TestNativeCheckpointHandler:
    """Tests for _process_native_checkpoint."""

    def test_processes_checkpoint_event(self):
        """Should emit correct checkpoint event format."""
        result_queue = queue.Queue()
        event_data = {
            "name": "state_snapshot",
            "data": {"state": {"count": 5}},
        }

        _process_native_checkpoint(event_data, result_queue)

        event = result_queue.get_nowait()
        assert event["type"] == "checkpoint"
        assert event["name"] == "state_snapshot"
        assert event["data"] == {"state": {"count": 5}}

    def test_handles_missing_fields(self):
        """Should handle missing fields with defaults."""
        result_queue = queue.Queue()

        _process_native_checkpoint({}, result_queue)

        event = result_queue.get_nowait()
        assert event["type"] == "checkpoint"
        assert event["name"] == ""
        assert event["data"] == {}


class TestNativeTokenHandler:
    """Tests for _process_native_token."""

    def test_processes_token_event(self):
        """Should emit correct token event format."""
        result_queue = queue.Queue()

        _process_native_token({"content": "Hello"}, result_queue)

        event = result_queue.get_nowait()
        assert event["type"] == "token"
        assert event["content"] == "Hello"


class TestNativeStepHandler:
    """Tests for _process_native_step."""

    def test_processes_step_event(self):
        """Should emit correct step event format."""
        result_queue = queue.Queue()
        event_data = {
            "node_name": "process_node",
            "output": {"result": "done"},
        }

        _process_native_step(event_data, result_queue)

        event = result_queue.get_nowait()
        assert event["type"] == "step"
        assert event["node"] == "process_node"
        assert event["output"] == {"result": "done"}

    def test_handles_node_key_variant(self):
        """Should handle 'node' key as alternative to 'node_name'."""
        result_queue = queue.Queue()
        event_data = {"node": "alt_node"}

        _process_native_step(event_data, result_queue)

        event = result_queue.get_nowait()
        assert event["node"] == "alt_node"


class TestNativeUserCustomHandler:
    """Tests for _process_native_user_custom."""

    def test_processes_custom_event(self):
        """Should emit correct custom event format."""
        result_queue = queue.Queue()

        _process_native_user_custom(
            "fraud_check",
            {"risk_score": 0.8, "flagged": True},
            result_queue,
        )

        event = result_queue.get_nowait()
        assert event["type"] == "custom"
        assert event["event_type"] == "fraud_check"
        assert event["data"]["risk_score"] == 0.8


class TestNativeEventHandlersRegistry:
    """Tests for the _NATIVE_EVENT_HANDLERS registry."""

    def test_contains_known_event_types(self):
        """Registry should contain handlers for known types."""
        assert "progress" in _NATIVE_EVENT_HANDLERS
        assert "checkpoint" in _NATIVE_EVENT_HANDLERS
        assert "token" in _NATIVE_EVENT_HANDLERS
        assert "step" in _NATIVE_EVENT_HANDLERS


class TestProcessNativeCustomMode:
    """Tests for _process_native_custom_mode."""

    def test_routes_progress_event(self):
        """Should route progress event to handler."""
        result_queue = queue.Queue()
        data = ("progress", {"step": "test", "progress": 0.5})
        logger = MagicMock()

        _process_native_custom_mode(data, result_queue, None, logger)

        event = result_queue.get_nowait()
        assert event["type"] == "progress"

    def test_routes_checkpoint_event(self):
        """Should route checkpoint event to handler."""
        result_queue = queue.Queue()
        data = ("checkpoint", {"name": "snap", "data": {}})
        logger = MagicMock()

        _process_native_custom_mode(data, result_queue, None, logger)

        event = result_queue.get_nowait()
        assert event["type"] == "checkpoint"

    def test_routes_user_custom_event(self):
        """Should route custom:name events to user custom handler."""
        result_queue = queue.Queue()
        data = ("custom:fraud_check", {"risk": 0.9})
        logger = MagicMock()

        _process_native_custom_mode(data, result_queue, None, logger)

        event = result_queue.get_nowait()
        assert event["type"] == "custom"
        assert event["event_type"] == "fraud_check"

    def test_handles_unknown_event_type(self):
        """Should treat unknown types as custom events."""
        result_queue = queue.Queue()
        data = ("unknown_type", {"value": 123})
        logger = MagicMock()

        _process_native_custom_mode(data, result_queue, None, logger)

        event = result_queue.get_nowait()
        assert event["type"] == "custom"
        assert event["event_type"] == "unknown_type"

    def test_filters_disallowed_events(self):
        """Should filter events based on events_filter."""
        from dockrion_events import EventsFilter

        result_queue = queue.Queue()
        data = ("progress", {"step": "test", "progress": 0.5})
        logger = MagicMock()

        # Filter that doesn't allow progress
        events_filter = EventsFilter(["token", "step"])

        _process_native_custom_mode(data, result_queue, events_filter, logger)

        # Queue should be empty since progress is filtered
        assert result_queue.empty()

    def test_allows_events_matching_filter(self):
        """Should allow events that pass filter."""
        from dockrion_events import EventsFilter

        result_queue = queue.Queue()
        data = ("progress", {"step": "test", "progress": 0.5})
        logger = MagicMock()

        # Filter that allows progress
        events_filter = EventsFilter(["progress"])

        _process_native_custom_mode(data, result_queue, events_filter, logger)

        event = result_queue.get_nowait()
        assert event["type"] == "progress"

    def test_handles_invalid_format(self):
        """Should handle invalid data format gracefully."""
        result_queue = queue.Queue()
        logger = MagicMock()

        # Invalid: not a tuple
        _process_native_custom_mode("invalid", result_queue, None, logger)
        assert result_queue.empty()

        # Invalid: wrong tuple length
        _process_native_custom_mode(("single",), result_queue, None, logger)
        assert result_queue.empty()

    def test_handles_non_dict_event_data(self):
        """Should wrap non-dict event_data in a dict."""
        result_queue = queue.Queue()
        data = ("custom:test", "string_value")
        logger = MagicMock()

        _process_native_custom_mode(data, result_queue, None, logger)

        event = result_queue.get_nowait()
        assert event["data"]["value"] == "string_value"
