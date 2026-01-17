"""
Tests for StreamingEventsConfig schema validation.

Tests cover:
- Default configuration (null = all events)
- Preset string validation
- Explicit list validation
- Custom event patterns
- Invalid configurations
"""

import pytest
from dockrion_common.errors import ValidationError

from dockrion_schema import StreamingConfig, StreamingEventsConfig


class TestStreamingEventsConfigDefaults:
    """Test default configuration."""

    def test_events_allowed_null_default(self):
        """Default allowed should be None (all events)."""
        config = StreamingEventsConfig()
        assert config.allowed is None

    def test_heartbeat_interval_default(self):
        """Default heartbeat interval should be 15 seconds."""
        config = StreamingEventsConfig()
        assert config.heartbeat_interval == 15

    def test_max_run_duration_default(self):
        """Default max run duration should be 3600 seconds."""
        config = StreamingEventsConfig()
        assert config.max_run_duration == 3600


class TestStreamingEventsConfigPresets:
    """Test preset string validation."""

    def test_events_allowed_preset_all(self):
        """'all' preset should be valid."""
        config = StreamingEventsConfig(allowed="all")
        assert config.allowed == "all"

    def test_events_allowed_preset_chat(self):
        """'chat' preset should be valid."""
        config = StreamingEventsConfig(allowed="chat")
        assert config.allowed == "chat"

    def test_events_allowed_preset_debug(self):
        """'debug' preset should be valid."""
        config = StreamingEventsConfig(allowed="debug")
        assert config.allowed == "debug"

    def test_events_allowed_preset_minimal(self):
        """'minimal' preset should be valid."""
        config = StreamingEventsConfig(allowed="minimal")
        assert config.allowed == "minimal"

    def test_invalid_preset_raises_error(self):
        """Invalid preset name should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingEventsConfig(allowed="invalid_preset")
        assert "Unknown events preset" in str(exc_info.value)


class TestStreamingEventsConfigExplicitList:
    """Test explicit list validation."""

    def test_events_allowed_explicit_list(self):
        """Explicit list of event types should be valid."""
        config = StreamingEventsConfig(allowed=["token", "step"])
        assert config.allowed == ["token", "step"]

    def test_events_allowed_single_item_list(self):
        """Single item list should be valid."""
        config = StreamingEventsConfig(allowed=["token"])
        assert config.allowed == ["token"]

    def test_events_allowed_all_valid_types(self):
        """All valid event types should be accepted."""
        config = StreamingEventsConfig(
            allowed=["token", "step", "progress", "checkpoint", "heartbeat"]
        )
        assert len(config.allowed) == 5

    def test_events_allowed_empty_list(self):
        """Empty list should be valid (minimal mode)."""
        config = StreamingEventsConfig(allowed=[])
        assert config.allowed == []

    def test_invalid_event_type_raises_error(self):
        """Unknown event type should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingEventsConfig(allowed=["token", "invalid_event"])
        assert "Unknown event type" in str(exc_info.value)


class TestStreamingEventsConfigCustomEvents:
    """Test custom event pattern validation."""

    def test_events_allowed_with_custom_wildcard(self):
        """'custom' wildcard should be valid."""
        config = StreamingEventsConfig(allowed=["token", "custom"])
        assert "custom" in config.allowed

    def test_events_allowed_with_specific_custom(self):
        """'custom:name' pattern should be valid."""
        config = StreamingEventsConfig(allowed=["token", "custom:fraud_check"])
        assert "custom:fraud_check" in config.allowed

    def test_events_allowed_multiple_custom(self):
        """Multiple custom:name patterns should be valid."""
        config = StreamingEventsConfig(
            allowed=["custom:fraud_check", "custom:analytics", "custom:logging"]
        )
        assert len(config.allowed) == 3

    def test_custom_with_valid_identifier(self):
        """Custom event with valid identifier should be accepted."""
        config = StreamingEventsConfig(allowed=["custom:my_event_123"])
        assert config.allowed == ["custom:my_event_123"]

    def test_custom_empty_name_raises_error(self):
        """'custom:' with empty name should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingEventsConfig(allowed=["custom:"])
        assert "Custom event name cannot be empty" in str(exc_info.value)

    def test_custom_invalid_identifier_raises_error(self):
        """'custom:' with invalid identifier should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingEventsConfig(allowed=["custom:123-invalid"])
        assert "Invalid custom event name" in str(exc_info.value)


class TestStreamingEventsConfigMandatoryEvents:
    """Test mandatory events handling."""

    def test_mandatory_events_in_list_accepted(self):
        """Mandatory events in list should be accepted (but ignored)."""
        # Mandatory events can be in the list but are always allowed anyway
        config = StreamingEventsConfig(allowed=["started", "token"])
        assert "started" in config.allowed
        assert "token" in config.allowed


class TestStreamingEventsConfigValidation:
    """Test field validation."""

    def test_heartbeat_interval_valid_range(self):
        """Heartbeat interval within range should be valid."""
        config = StreamingEventsConfig(heartbeat_interval=30)
        assert config.heartbeat_interval == 30

    def test_heartbeat_interval_too_low_raises_error(self):
        """Heartbeat interval below 1 should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingEventsConfig(heartbeat_interval=0)
        assert "heartbeat_interval must be between" in str(exc_info.value)

    def test_heartbeat_interval_too_high_raises_error(self):
        """Heartbeat interval above 300 should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingEventsConfig(heartbeat_interval=301)
        assert "heartbeat_interval must be between" in str(exc_info.value)

    def test_max_run_duration_valid_range(self):
        """Max run duration within range should be valid."""
        config = StreamingEventsConfig(max_run_duration=7200)
        assert config.max_run_duration == 7200

    def test_max_run_duration_too_low_raises_error(self):
        """Max run duration below 1 should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingEventsConfig(max_run_duration=0)
        assert "max_run_duration must be between" in str(exc_info.value)

    def test_max_run_duration_too_high_raises_error(self):
        """Max run duration above 86400 should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingEventsConfig(max_run_duration=86401)
        assert "max_run_duration must be between" in str(exc_info.value)


class TestStreamingConfigIntegration:
    """Test StreamingConfig with events configuration."""

    def test_streaming_config_with_events_preset(self):
        """StreamingConfig should accept events preset."""
        config = StreamingConfig(
            async_runs=True,
            backend="memory",
            events=StreamingEventsConfig(allowed="chat"),
        )
        assert config.events.allowed == "chat"

    def test_streaming_config_with_events_list(self):
        """StreamingConfig should accept events list."""
        config = StreamingConfig(
            async_runs=True,
            events=StreamingEventsConfig(allowed=["token", "step", "custom:fraud"]),
        )
        assert config.events.allowed == ["token", "step", "custom:fraud"]

    def test_streaming_config_without_events(self):
        """StreamingConfig without events should use defaults."""
        config = StreamingConfig(async_runs=True)
        assert config.events is None or config.events.allowed is None

    def test_streaming_config_from_dict(self):
        """StreamingConfig should parse from dict correctly."""
        data = {
            "async_runs": True,
            "backend": "memory",
            "events": {
                "allowed": "chat",
                "heartbeat_interval": 30,
            },
        }
        config = StreamingConfig.model_validate(data)
        assert config.events.allowed == "chat"
        assert config.events.heartbeat_interval == 30


class TestStreamingEventsConfigSerialization:
    """Test serialization and deserialization."""

    def test_serialize_preset(self):
        """Preset should serialize correctly."""
        config = StreamingEventsConfig(allowed="chat")
        data = config.model_dump()
        assert data["allowed"] == "chat"

    def test_serialize_list(self):
        """List should serialize correctly."""
        config = StreamingEventsConfig(allowed=["token", "step"])
        data = config.model_dump()
        assert data["allowed"] == ["token", "step"]

    def test_serialize_none(self):
        """None should serialize correctly."""
        config = StreamingEventsConfig()
        data = config.model_dump()
        assert data["allowed"] is None

    def test_deserialize_preset(self):
        """Preset should deserialize correctly."""
        config = StreamingEventsConfig.model_validate({"allowed": "debug"})
        assert config.allowed == "debug"

    def test_deserialize_list(self):
        """List should deserialize correctly."""
        config = StreamingEventsConfig.model_validate(
            {"allowed": ["token", "custom:fraud_check"]}
        )
        assert config.allowed == ["token", "custom:fraud_check"]
