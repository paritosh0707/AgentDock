"""
Events Filter Module

Determines which events are allowed based on Dockfile configuration.
Provides allow-list based filtering with preset support.

Usage:
    from dockrion_events import EventsFilter

    # Default: all events allowed
    filter = EventsFilter(None)

    # Preset
    filter = EventsFilter("chat")  # token, step, heartbeat

    # Explicit list
    filter = EventsFilter(["token", "step", "custom:fraud_check"])

    # Check if event is allowed
    if filter.is_allowed("token"):
        emit_token(...)

    # Get LangGraph stream modes
    modes = filter.get_langgraph_stream_modes()  # ["messages", "updates"]
"""

from typing import List, Optional, Set, Union

from dockrion_common import get_logger

logger = get_logger("events.filter")


class EventsFilter:
    """
    Determines which events are allowed based on Dockfile configuration.

    Events are classified as:
    - Mandatory: Always emitted (started, complete, error, cancelled)
    - Configurable: Can be enabled/disabled via config

    Configuration can be:
    - None: All events allowed (default)
    - str: Preset name ("all", "chat", "debug", "minimal")
    - List[str]: Explicit list of allowed events

    For custom events:
    - "custom" in list: All custom events allowed
    - "custom:name" in list: Only specific custom event allowed

    Attributes:
        MANDATORY_EVENTS: Set of events that are always emitted
        PRESETS: Dict mapping preset names to allowed event sets
    """

    # Events that are ALWAYS emitted regardless of configuration
    # These are essential for run lifecycle management
    MANDATORY_EVENTS: Set[str] = {"started", "complete", "error", "cancelled"}

    # Built-in configurable event types
    CONFIGURABLE_EVENTS: Set[str] = {"token", "step", "progress", "checkpoint", "heartbeat"}

    # Presets for common use cases
    PRESETS = {
        "minimal": set(),  # Only mandatory events
        "chat": {"token", "step", "progress", "heartbeat"},  # Optimized for chat UIs
        "debug": {"token", "step", "progress", "checkpoint", "heartbeat", "custom"},  # Everything
        "all": {"token", "step", "progress", "checkpoint", "heartbeat", "custom"},  # Everything
    }

    def __init__(self, events_config: Optional[Union[List[str], str]] = None):
        """
        Initialize EventsFilter from configuration.

        Args:
            events_config: Can be:
                - None: All events allowed (default)
                - str: Preset name ("all", "chat", "debug", "minimal")
                - List[str]: Explicit list of allowed events
                  Examples: ["token", "step"], ["token", "custom:fraud_check"]

        Raises:
            ValueError: If preset name is invalid or event type is unknown
        """
        self._allowed_builtin: Set[str] = set()
        self._custom_whitelist: Optional[Set[str]] = None  # None = all custom allowed

        if events_config is None:
            # Default: all events allowed
            self._allowed_builtin = self.CONFIGURABLE_EVENTS.copy()
            self._custom_whitelist = None  # All custom allowed
            logger.debug("EventsFilter initialized with all events allowed (default)")

        elif isinstance(events_config, str):
            # Preset name
            if events_config not in self.PRESETS:
                valid_presets = ", ".join(sorted(self.PRESETS.keys()))
                raise ValueError(
                    f"Unknown events preset: '{events_config}'. "
                    f"Valid presets: {valid_presets}"
                )
            preset = self.PRESETS[events_config]
            self._allowed_builtin = preset - {"custom"}
            self._custom_whitelist = None if "custom" in preset else set()
            logger.debug(
                f"EventsFilter initialized with preset '{events_config}'",
                allowed=sorted(self._allowed_builtin),
                custom_allowed="all" if self._custom_whitelist is None else "none",
            )

        else:
            # Explicit list
            self._parse_explicit_list(events_config)
            logger.debug(
                "EventsFilter initialized with explicit list",
                allowed=sorted(self._allowed_builtin),
                custom_whitelist=(
                    "all"
                    if self._custom_whitelist is None
                    else sorted(self._custom_whitelist) if self._custom_whitelist else "none"
                ),
            )

    def _parse_explicit_list(self, events: List[str]) -> None:
        """
        Parse an explicit list of event types.

        Args:
            events: List of event type strings

        Raises:
            ValueError: If an event type is invalid
        """
        self._allowed_builtin = set()
        self._custom_whitelist = set()

        for event in events:
            if event.startswith("custom:"):
                # Specific custom event: "custom:fraud_check"
                custom_name = event[7:]  # Remove "custom:" prefix
                if not custom_name:
                    raise ValueError("Custom event name cannot be empty in 'custom:'")
                if self._custom_whitelist is not None:
                    self._custom_whitelist.add(custom_name)
            elif event == "custom":
                # Wildcard: all custom events allowed
                self._custom_whitelist = None
            elif event in self.CONFIGURABLE_EVENTS:
                # Built-in configurable event
                self._allowed_builtin.add(event)
            elif event in self.MANDATORY_EVENTS:
                # Mandatory events are always allowed, no need to add
                logger.debug(f"Event '{event}' is mandatory and always allowed")
            else:
                valid_events = sorted(self.CONFIGURABLE_EVENTS | {"custom", "custom:<name>"})
                raise ValueError(
                    f"Unknown event type: '{event}'. "
                    f"Valid types: {', '.join(valid_events)}"
                )

    def is_allowed(self, event_type: str, custom_event_name: Optional[str] = None) -> bool:
        """
        Check if an event type is allowed by the filter.

        Args:
            event_type: The event type (e.g., "token", "step", "progress")
            custom_event_name: For custom events, the specific event name

        Returns:
            True if the event should be emitted, False if it should be skipped

        Examples:
            >>> filter = EventsFilter(["token", "step"])
            >>> filter.is_allowed("token")
            True
            >>> filter.is_allowed("progress")
            False
            >>> filter.is_allowed("started")  # Mandatory
            True
        """
        # Mandatory events are ALWAYS allowed
        if event_type in self.MANDATORY_EVENTS:
            return True

        # Check built-in configurable events
        if event_type in self._allowed_builtin:
            return True

        # Check custom events
        if event_type == "custom" or custom_event_name is not None:
            if self._custom_whitelist is None:
                return True  # All custom events allowed
            name = custom_event_name if custom_event_name else event_type
            return name in self._custom_whitelist

        return False

    def get_langgraph_stream_modes(self) -> List[str]:
        """
        Get LangGraph stream_mode list based on allowed events.

        Maps Dockrion event types to LangGraph stream modes:
        - token -> "messages" (token-by-token LLM streaming)
        - step -> "updates" (node completion events)
        - progress, checkpoint, custom -> "custom" (native backend events)

        Returns:
            List of LangGraph stream modes to use.
            Returns ["values"] if no streaming events are enabled.

        Examples:
            >>> filter = EventsFilter(["token", "step"])
            >>> filter.get_langgraph_stream_modes()
            ["messages", "updates"]

            >>> filter = EventsFilter("minimal")
            >>> filter.get_langgraph_stream_modes()
            ["values"]
        """
        modes = []

        if "token" in self._allowed_builtin:
            modes.append("messages")

        if "step" in self._allowed_builtin:
            modes.append("updates")

        # Add "custom" mode for native backend events (progress, checkpoint, custom)
        needs_custom_mode = (
            "progress" in self._allowed_builtin
            or "checkpoint" in self._allowed_builtin
            or self._custom_whitelist is None  # All custom allowed
            or bool(self._custom_whitelist)  # Specific custom events allowed
        )
        if needs_custom_mode:
            modes.append("custom")

        # If no streaming events enabled, use "values" for final state only
        if not modes:
            modes = ["values"]

        return modes

    def is_native_event_allowed(self, langgraph_mode: str, inner_type: str = "") -> bool:
        """
        Check if event from LangGraph native streaming is allowed.

        When using native LangGraph backend, events come through different modes:
        - "messages" -> token events
        - "updates" -> step events
        - "custom" -> progress, checkpoint, user custom events

        Args:
            langgraph_mode: LangGraph stream mode ("messages", "updates", "custom", "values")
            inner_type: For "custom" mode, the inner event type (e.g., "progress", "custom:fraud")

        Returns:
            True if event should be emitted

        Examples:
            >>> filter = EventsFilter(["token", "progress"])
            >>> filter.is_native_event_allowed("messages", "")
            True
            >>> filter.is_native_event_allowed("custom", "progress")
            True
            >>> filter.is_native_event_allowed("custom", "checkpoint")
            False
        """
        if langgraph_mode == "messages":
            return self.is_allowed("token")

        if langgraph_mode == "updates":
            return self.is_allowed("step")

        if langgraph_mode == "custom":
            if inner_type.startswith("custom:"):
                # User custom event: "custom:fraud_check"
                custom_name = inner_type[7:]
                return self.is_allowed("custom", custom_name)
            else:
                # Known event type (progress, checkpoint)
                return self.is_allowed(inner_type)

        if langgraph_mode == "values":
            return True  # Final state always allowed

        return False

    @property
    def allows_tokens(self) -> bool:
        """Check if token events are allowed."""
        return "token" in self._allowed_builtin

    @property
    def allows_steps(self) -> bool:
        """Check if step events are allowed."""
        return "step" in self._allowed_builtin

    @property
    def allows_progress(self) -> bool:
        """Check if progress events are allowed."""
        return "progress" in self._allowed_builtin

    @property
    def allows_checkpoints(self) -> bool:
        """Check if checkpoint events are allowed."""
        return "checkpoint" in self._allowed_builtin

    @property
    def allows_heartbeats(self) -> bool:
        """Check if heartbeat events are allowed."""
        return "heartbeat" in self._allowed_builtin

    @property
    def allows_all_custom(self) -> bool:
        """Check if all custom events are allowed."""
        return self._custom_whitelist is None

    def get_allowed_events(self) -> Set[str]:
        """
        Get the set of all allowed event types.

        Returns:
            Set of allowed event type names (including mandatory)
        """
        allowed = self.MANDATORY_EVENTS.copy()
        allowed.update(self._allowed_builtin)
        if self._custom_whitelist is None:
            allowed.add("custom")
        return allowed

    def __repr__(self) -> str:
        """String representation for debugging."""
        if self._allowed_builtin == self.CONFIGURABLE_EVENTS and self._custom_whitelist is None:
            return "EventsFilter(all)"

        for preset_name, preset_events in self.PRESETS.items():
            builtin_match = self._allowed_builtin == (preset_events - {"custom"})
            custom_match = (
                self._custom_whitelist is None
                if "custom" in preset_events
                else self._custom_whitelist == set()
            )
            if builtin_match and custom_match:
                return f"EventsFilter(preset='{preset_name}')"

        events = sorted(self._allowed_builtin)
        if self._custom_whitelist is None:
            events.append("custom")
        elif self._custom_whitelist:
            events.extend(f"custom:{name}" for name in sorted(self._custom_whitelist))

        return f"EventsFilter({events})"
