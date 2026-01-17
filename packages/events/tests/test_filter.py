"""
Tests for EventsFilter module.

Tests cover:
- Default configuration (all events allowed)
- Preset configurations (chat, debug, minimal, all)
- Explicit list configurations
- Custom event filtering
- Mandatory events behavior
- LangGraph stream mode mapping
"""

import pytest

from dockrion_events import EventsFilter


class TestEventsFilterDefault:
    """Test default configuration (no filter = all events)."""

    def test_default_allows_all_configurable_events(self):
        """Default filter should allow all configurable events."""
        filter = EventsFilter(None)

        assert filter.is_allowed("token")
        assert filter.is_allowed("step")
        assert filter.is_allowed("progress")
        assert filter.is_allowed("checkpoint")
        assert filter.is_allowed("heartbeat")

    def test_default_allows_all_mandatory_events(self):
        """Default filter should always allow mandatory events."""
        filter = EventsFilter(None)

        assert filter.is_allowed("started")
        assert filter.is_allowed("complete")
        assert filter.is_allowed("error")
        assert filter.is_allowed("cancelled")

    def test_default_allows_all_custom_events(self):
        """Default filter should allow all custom events."""
        filter = EventsFilter(None)

        assert filter.is_allowed("custom", "my_event")
        assert filter.is_allowed("custom", "fraud_check")
        assert filter.allows_all_custom


class TestEventsFilterPresets:
    """Test preset configurations."""

    def test_preset_chat_allows_token_step_heartbeat(self):
        """Chat preset should allow token, step, heartbeat."""
        filter = EventsFilter("chat")

        assert filter.is_allowed("token")
        assert filter.is_allowed("step")
        assert filter.is_allowed("heartbeat")

    def test_preset_chat_allows_progress_denies_checkpoint(self):
        """Chat preset should allow progress but deny checkpoint."""
        filter = EventsFilter("chat")

        # Chat includes progress for user feedback
        assert filter.is_allowed("progress")
        # Checkpoint is verbose, not needed for chat
        assert not filter.is_allowed("checkpoint")

    def test_preset_chat_denies_custom(self):
        """Chat preset should deny custom events."""
        filter = EventsFilter("chat")

        assert not filter.is_allowed("custom", "my_event")
        assert not filter.allows_all_custom

    def test_preset_minimal_allows_only_mandatory(self):
        """Minimal preset should only allow mandatory events."""
        filter = EventsFilter("minimal")

        # Mandatory are always allowed
        assert filter.is_allowed("started")
        assert filter.is_allowed("complete")
        assert filter.is_allowed("error")
        assert filter.is_allowed("cancelled")

        # Configurable should be denied
        assert not filter.is_allowed("token")
        assert not filter.is_allowed("step")
        assert not filter.is_allowed("progress")
        assert not filter.is_allowed("checkpoint")
        assert not filter.is_allowed("heartbeat")

    def test_preset_debug_allows_all_including_custom(self):
        """Debug preset should allow all events including custom."""
        filter = EventsFilter("debug")

        assert filter.is_allowed("token")
        assert filter.is_allowed("step")
        assert filter.is_allowed("progress")
        assert filter.is_allowed("checkpoint")
        assert filter.is_allowed("heartbeat")
        assert filter.is_allowed("custom", "my_event")
        assert filter.allows_all_custom

    def test_preset_all_same_as_debug(self):
        """'all' preset should behave same as debug."""
        filter = EventsFilter("all")

        assert filter.is_allowed("token")
        assert filter.is_allowed("step")
        assert filter.is_allowed("progress")
        assert filter.is_allowed("checkpoint")
        assert filter.is_allowed("heartbeat")
        assert filter.is_allowed("custom", "my_event")

    def test_invalid_preset_raises_error(self):
        """Invalid preset name should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EventsFilter("invalid_preset")

        assert "Unknown events preset" in str(exc_info.value)
        assert "invalid_preset" in str(exc_info.value)


class TestEventsFilterExplicitList:
    """Test explicit list configurations."""

    def test_explicit_list_filters_correctly(self):
        """Explicit list should only allow specified events."""
        filter = EventsFilter(["token", "step"])

        assert filter.is_allowed("token")
        assert filter.is_allowed("step")
        assert not filter.is_allowed("progress")
        assert not filter.is_allowed("checkpoint")
        assert not filter.is_allowed("heartbeat")

    def test_explicit_list_always_allows_mandatory(self):
        """Mandatory events should be allowed even if not in list."""
        filter = EventsFilter(["token"])

        # Only token is specified, but mandatory are always allowed
        assert filter.is_allowed("started")
        assert filter.is_allowed("complete")
        assert filter.is_allowed("error")
        assert filter.is_allowed("cancelled")

    def test_explicit_list_with_heartbeat_only(self):
        """List with only heartbeat should work correctly."""
        filter = EventsFilter(["heartbeat"])

        assert filter.is_allowed("heartbeat")
        assert not filter.is_allowed("token")
        assert not filter.is_allowed("step")

    def test_empty_list_like_minimal(self):
        """Empty list should behave like minimal preset."""
        filter = EventsFilter([])

        # Mandatory are always allowed
        assert filter.is_allowed("started")

        # Nothing else
        assert not filter.is_allowed("token")
        assert not filter.is_allowed("step")

    def test_invalid_event_type_raises_error(self):
        """Unknown event type in list should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EventsFilter(["token", "invalid_event"])

        assert "Unknown event type" in str(exc_info.value)
        assert "invalid_event" in str(exc_info.value)


class TestEventsFilterCustomEvents:
    """Test custom event filtering."""

    def test_custom_wildcard_allows_all_custom(self):
        """'custom' in list should allow all custom events."""
        filter = EventsFilter(["token", "custom"])

        assert filter.is_allowed("custom", "any_event")
        assert filter.is_allowed("custom", "fraud_check")
        assert filter.is_allowed("custom", "analytics")
        assert filter.allows_all_custom

    def test_custom_specific_whitelist(self):
        """'custom:name' should only allow that specific custom event."""
        filter = EventsFilter(["token", "custom:fraud_check"])

        assert filter.is_allowed("custom", "fraud_check")
        assert not filter.is_allowed("custom", "other_event")
        assert not filter.allows_all_custom

    def test_multiple_custom_specific(self):
        """Multiple 'custom:name' entries should work."""
        filter = EventsFilter(["custom:fraud_check", "custom:analytics"])

        assert filter.is_allowed("custom", "fraud_check")
        assert filter.is_allowed("custom", "analytics")
        assert not filter.is_allowed("custom", "other_event")

    def test_custom_empty_name_raises_error(self):
        """'custom:' with empty name should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EventsFilter(["custom:"])

        assert "Custom event name cannot be empty" in str(exc_info.value)

    def test_custom_without_filter_allows_none(self):
        """If 'custom' not in list, custom events should be denied."""
        filter = EventsFilter(["token", "step"])

        assert not filter.is_allowed("custom", "any_event")


class TestMandatoryEvents:
    """Test mandatory events are always allowed."""

    @pytest.mark.parametrize(
        "config",
        [
            None,
            "minimal",
            "chat",
            [],
            ["token"],
        ],
    )
    def test_started_always_allowed(self, config):
        """'started' should always be allowed regardless of config."""
        filter = EventsFilter(config)
        assert filter.is_allowed("started")

    @pytest.mark.parametrize(
        "config",
        [
            None,
            "minimal",
            "chat",
            [],
            ["token"],
        ],
    )
    def test_complete_always_allowed(self, config):
        """'complete' should always be allowed regardless of config."""
        filter = EventsFilter(config)
        assert filter.is_allowed("complete")

    @pytest.mark.parametrize(
        "config",
        [
            None,
            "minimal",
            "chat",
            [],
            ["token"],
        ],
    )
    def test_error_always_allowed(self, config):
        """'error' should always be allowed regardless of config."""
        filter = EventsFilter(config)
        assert filter.is_allowed("error")

    @pytest.mark.parametrize(
        "config",
        [
            None,
            "minimal",
            "chat",
            [],
            ["token"],
        ],
    )
    def test_cancelled_always_allowed(self, config):
        """'cancelled' should always be allowed regardless of config."""
        filter = EventsFilter(config)
        assert filter.is_allowed("cancelled")


class TestLangGraphStreamModes:
    """Test LangGraph stream mode mapping."""

    def test_token_maps_to_messages(self):
        """Filter with token should include 'messages' mode."""
        filter = EventsFilter(["token"])
        modes = filter.get_langgraph_stream_modes()

        assert "messages" in modes

    def test_step_maps_to_updates(self):
        """Filter with step should include 'updates' mode."""
        filter = EventsFilter(["step"])
        modes = filter.get_langgraph_stream_modes()

        assert "updates" in modes

    def test_token_and_step_maps_to_both(self):
        """Filter with both should include both modes."""
        filter = EventsFilter(["token", "step"])
        modes = filter.get_langgraph_stream_modes()

        assert "messages" in modes
        assert "updates" in modes

    def test_minimal_returns_values_only(self):
        """Minimal preset should return only 'values' mode."""
        filter = EventsFilter("minimal")
        modes = filter.get_langgraph_stream_modes()

        assert modes == ["values"]

    def test_progress_only_returns_custom(self):
        """Progress-only filter should return 'custom' for native backend events."""
        filter = EventsFilter(["progress"])
        modes = filter.get_langgraph_stream_modes()

        # Progress events come through "custom" mode from native backend
        assert modes == ["custom"]

    def test_chat_preset_modes(self):
        """Chat preset should return messages, updates, and custom."""
        filter = EventsFilter("chat")
        modes = filter.get_langgraph_stream_modes()

        assert "messages" in modes  # token
        assert "updates" in modes  # step
        assert "custom" in modes  # progress


class TestEventsFilterProperties:
    """Test convenience properties."""

    def test_allows_tokens_property(self):
        """allows_tokens property should reflect filter state."""
        assert EventsFilter(["token"]).allows_tokens
        assert not EventsFilter(["step"]).allows_tokens
        assert EventsFilter("chat").allows_tokens

    def test_allows_steps_property(self):
        """allows_steps property should reflect filter state."""
        assert EventsFilter(["step"]).allows_steps
        assert not EventsFilter(["token"]).allows_steps
        assert EventsFilter("chat").allows_steps

    def test_allows_progress_property(self):
        """allows_progress property should reflect filter state."""
        assert EventsFilter(["progress"]).allows_progress
        assert not EventsFilter(["token"]).allows_progress
        assert EventsFilter("debug").allows_progress

    def test_allows_checkpoints_property(self):
        """allows_checkpoints property should reflect filter state."""
        assert EventsFilter(["checkpoint"]).allows_checkpoints
        assert not EventsFilter(["token"]).allows_checkpoints
        assert EventsFilter("debug").allows_checkpoints

    def test_allows_heartbeats_property(self):
        """allows_heartbeats property should reflect filter state."""
        assert EventsFilter(["heartbeat"]).allows_heartbeats
        assert not EventsFilter(["token"]).allows_heartbeats
        assert EventsFilter("chat").allows_heartbeats


class TestEventsFilterRepr:
    """Test string representation."""

    def test_repr_default(self):
        """Default filter should have clear repr."""
        filter = EventsFilter(None)
        repr_str = repr(filter)

        assert "EventsFilter" in repr_str

    def test_repr_preset(self):
        """Preset filter should show preset name."""
        filter = EventsFilter("chat")
        repr_str = repr(filter)

        assert "EventsFilter" in repr_str
        assert "chat" in repr_str

    def test_repr_explicit_list(self):
        """Explicit list should show events."""
        filter = EventsFilter(["token", "step"])
        repr_str = repr(filter)

        assert "EventsFilter" in repr_str


class TestGetAllowedEvents:
    """Test get_allowed_events method."""

    def test_get_allowed_includes_mandatory(self):
        """get_allowed_events should include mandatory events."""
        filter = EventsFilter(["token"])
        allowed = filter.get_allowed_events()

        assert "started" in allowed
        assert "complete" in allowed
        assert "error" in allowed
        assert "cancelled" in allowed
        assert "token" in allowed

    def test_get_allowed_reflects_config(self):
        """get_allowed_events should reflect filter configuration."""
        filter = EventsFilter(["token", "step"])
        allowed = filter.get_allowed_events()

        assert "token" in allowed
        assert "step" in allowed
        assert "progress" not in allowed

    def test_get_allowed_includes_custom_wildcard(self):
        """get_allowed_events should include 'custom' if all custom allowed."""
        filter = EventsFilter(["token", "custom"])
        allowed = filter.get_allowed_events()

        assert "custom" in allowed
