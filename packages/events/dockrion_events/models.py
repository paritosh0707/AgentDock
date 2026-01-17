"""
Event Models for Dockrion Streaming

This module defines Pydantic models for all event types emitted during
agent execution. Events follow a common base structure with type-specific
extensions.

All events share:
    - id: Unique event identifier (UUID)
    - type: Event type string
    - run_id: Parent run identifier
    - sequence: Ordering sequence within run
    - timestamp: ISO8601 timestamp

Event Types:
    - started: Run begins execution
    - progress: Execution progress update
    - checkpoint: Intermediate state snapshot
    - token: LLM token for streaming
    - step: Agent step/node completion
    - complete: Successful completion
    - error: Execution failure
    - heartbeat: Keep-alive signal
    - cancelled: Run was cancelled

Usage:
    from dockrion_events.models import ProgressEvent, parse_event

    # Create an event
    event = ProgressEvent(
        run_id="run-123",
        step="parsing",
        progress=0.5,
        message="Halfway done"
    )

    # Parse event from dict
    event = parse_event(event_dict)
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from typing_extensions import Annotated


def _generate_event_id() -> str:
    """Generate a unique event ID."""
    return f"evt-{uuid.uuid4().hex[:12]}"


def _utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class BaseEvent(BaseModel):
    """
    Base class for all streaming events.

    All events share this common structure for consistent handling
    and serialization.

    Attributes:
        id: Unique event identifier (auto-generated UUID)
        type: Event type string (set by subclasses)
        run_id: Parent run identifier
        sequence: Ordering sequence within the run (auto-incremented)
        timestamp: ISO8601 timestamp (auto-generated)
    """

    id: str = Field(default_factory=_generate_event_id)
    type: str  # Discriminator field - subclasses will specify exact literal
    run_id: str
    sequence: int = 0
    timestamp: datetime = Field(default_factory=_utc_now)

    model_config = ConfigDict(extra="allow")

    @field_serializer("timestamp")
    @classmethod
    def serialize_datetime(cls, v: datetime) -> str:
        """Serialize datetime to ISO8601 format."""
        return v.isoformat()

    def to_sse(self) -> str:
        """Format event for Server-Sent Events."""
        data = self.model_dump_json()
        return f"event: {self.type}\ndata: {data}\n\n"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return self.model_dump(mode="json")


class StartedEvent(BaseEvent):
    """
    Emitted when a run begins execution.

    Attributes:
        agent_name: Name of the agent being executed
        framework: Agent framework (langgraph, custom, etc.)
    """

    type: Literal["started"] = Field(default="started", frozen=True)  # type: ignore[assignment]
    agent_name: Optional[str] = None
    framework: Optional[str] = None


class ProgressEvent(BaseEvent):
    """
    Indicates execution progress.

    Emitted by user code via StreamContext.emit_progress().

    Attributes:
        step: Current step/phase name
        progress: Progress percentage (0.0 to 1.0)
        message: Optional human-readable message
    """

    type: Literal["progress"] = Field(default="progress", frozen=True)  # type: ignore[assignment]
    step: str
    progress: float = 0.0
    message: Optional[str] = None

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v: float) -> float:
        """Ensure progress is between 0.0 and 1.0."""
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v


class CheckpointEvent(BaseEvent):
    """
    Captures intermediate state or data during execution.

    Emitted by user code via StreamContext.checkpoint().

    Attributes:
        name: Checkpoint identifier
        data: Checkpoint data payload
    """

    type: Literal["checkpoint"] = Field(default="checkpoint", frozen=True)  # type: ignore[assignment]
    name: str
    data: Dict[str, Any] = Field(default_factory=dict)


class TokenEvent(BaseEvent):
    """
    LLM token for streaming text generation.

    Emitted by LLM streaming integration or user code.

    Attributes:
        content: Token text content
        finish_reason: Why generation stopped (if final)
    """

    type: Literal["token"] = Field(default="token", frozen=True)  # type: ignore[assignment]
    content: str
    finish_reason: Optional[str] = None


class StepEvent(BaseEvent):
    """
    Indicates completion of an agent step (e.g., LangGraph node).

    Emitted by framework integration or user code.

    Attributes:
        node_name: Name of completed step/node
        duration_ms: Step execution time in milliseconds
        input_keys: Keys present in step input
        output_keys: Keys present in step output
    """

    type: Literal["step"] = Field(default="step", frozen=True)  # type: ignore[assignment]
    node_name: str
    duration_ms: Optional[int] = None
    input_keys: List[str] = Field(default_factory=list)
    output_keys: List[str] = Field(default_factory=list)


class CompleteEvent(BaseEvent):
    """
    Indicates successful run completion.

    Emitted automatically by the runtime when execution succeeds.

    Attributes:
        output: Final agent output
        latency_seconds: Total execution time
        metadata: Additional execution metadata
    """

    type: Literal["complete"] = Field(default="complete", frozen=True)  # type: ignore[assignment]
    output: Dict[str, Any] = Field(default_factory=dict)
    latency_seconds: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorEvent(BaseEvent):
    """
    Indicates run failure.

    Emitted automatically by the runtime on exception.

    Attributes:
        error: Error message
        code: Error code for programmatic handling
        details: Additional error context
    """

    type: Literal["error"] = Field(default="error", frozen=True)  # type: ignore[assignment]
    error: str
    code: str = "INTERNAL_ERROR"
    details: Optional[Dict[str, Any]] = None


class HeartbeatEvent(BaseEvent):
    """
    Keep-alive signal for long-running connections.

    Emitted automatically by the runtime at configured intervals.
    """

    type: Literal["heartbeat"] = Field(default="heartbeat", frozen=True)  # type: ignore[assignment]


class CancelledEvent(BaseEvent):
    """
    Indicates run was cancelled.

    Emitted by the runtime when a run is cancelled via API.

    Attributes:
        reason: Reason for cancellation
    """

    type: Literal["cancelled"] = Field(default="cancelled", frozen=True)  # type: ignore[assignment]
    reason: Optional[str] = None


# Type alias for all event types
StreamEvent = Union[
    StartedEvent,
    ProgressEvent,
    CheckpointEvent,
    TokenEvent,
    StepEvent,
    CompleteEvent,
    ErrorEvent,
    HeartbeatEvent,
    CancelledEvent,
]

# Terminal events that signal end of a run
TERMINAL_EVENT_TYPES = frozenset(["complete", "error", "cancelled"])


def is_terminal_event(event: BaseEvent) -> bool:
    """Check if event is a terminal event (signals end of run)."""
    return event.type in TERMINAL_EVENT_TYPES


# Event type registry for parsing
_EVENT_TYPE_MAP: Dict[str, type[BaseEvent]] = {
    "started": StartedEvent,
    "progress": ProgressEvent,
    "checkpoint": CheckpointEvent,
    "token": TokenEvent,
    "step": StepEvent,
    "complete": CompleteEvent,
    "error": ErrorEvent,
    "heartbeat": HeartbeatEvent,
    "cancelled": CancelledEvent,
}


def parse_event(data: Dict[str, Any]) -> BaseEvent:
    """
    Parse an event dictionary into the appropriate event model.

    Args:
        data: Event data dictionary with 'type' field

    Returns:
        Parsed event model instance

    Raises:
        ValueError: If event type is unknown

    Example:
        >>> event_dict = {"type": "progress", "run_id": "run-123", "step": "parsing", "progress": 0.5}
        >>> event = parse_event(event_dict)
        >>> isinstance(event, ProgressEvent)
        True
    """
    event_type = data.get("type")
    if not event_type:
        raise ValueError("Event data missing 'type' field")

    event_class = _EVENT_TYPE_MAP.get(event_type)
    if not event_class:
        # For custom events, use BaseEvent
        return BaseEvent(**data)

    return event_class(**data)


def create_event(
    event_type: str,
    run_id: str,
    sequence: int,
    **kwargs: Any,
) -> BaseEvent:
    """
    Factory function to create an event of the specified type.

    Args:
        event_type: Event type string
        run_id: Parent run identifier
        sequence: Sequence number within the run
        **kwargs: Additional event-specific fields

    Returns:
        Created event instance

    Example:
        >>> event = create_event("progress", "run-123", 5, step="parsing", progress=0.5)
    """
    event_class = _EVENT_TYPE_MAP.get(event_type, BaseEvent)
    return event_class(
        run_id=run_id,
        sequence=sequence,
        type=event_type,
        **kwargs,
    )
