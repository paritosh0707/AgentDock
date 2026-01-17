"""
Dockrion Events Package

Streaming and event infrastructure for Dockrion agent executions.

This package provides:
- Event models for representing execution events
- EventBus for routing events between publishers and subscribers
- StreamContext for user code to emit events
- EventsFilter for filtering events based on configuration
- Pluggable EventBus backends (InMemory, Redis)
- Streaming backends for native framework integration (LangGraph)
- RunManager for run lifecycle management

Public API:
    # Event Models
    - BaseEvent: Base class for all events
    - StartedEvent, ProgressEvent, CheckpointEvent, TokenEvent
    - StepEvent, CompleteEvent, ErrorEvent, HeartbeatEvent, CancelledEvent

    # Core Classes
    - EventBus: Event routing and delivery
    - StreamContext: User API for emitting events
    - EventsFilter: Filter to control which events are emitted
    - RunManager: Run lifecycle management

    # EventBus Backends (for Pattern B)
    - EventBackend: Backend protocol
    - InMemoryBackend: Development backend
    - RedisBackend: Production backend (requires redis extra)

    # Streaming Backends (for Pattern A native integration)
    - StreamingBackend: Protocol for streaming backends
    - LangGraphBackend: Native LangGraph streaming via get_stream_writer()
    - QueueBackend: Queue-based fallback for adapter draining

    # Context Access
    - get_current_context: Get thread-local StreamContext
    - set_current_context: Set thread-local StreamContext
    - context_scope: Context manager for StreamContext

Usage:
    from dockrion_events import (
        StreamContext,
        EventsFilter,
        LangGraphBackend,
        get_current_context,
    )

    # Pattern A with native LangGraph streaming
    backend = LangGraphBackend()
    context = StreamContext(
        run_id="run-123",
        queue_mode=True,
        events_filter=EventsFilter("chat"),
        streaming_backend=backend,
    )

    # Emit events (uses native backend if available)
    context.sync_emit_progress("parsing", 0.5, "Halfway done")
"""

from .backends import EventBackend, InMemoryBackend
from .bus import EventBus
from .context import (
    StreamContext,
    context_scope,
    get_current_context,
    set_current_context,
)
from .filter import EventsFilter
from .models import (
    BaseEvent,
    CancelledEvent,
    CheckpointEvent,
    CompleteEvent,
    ErrorEvent,
    HeartbeatEvent,
    ProgressEvent,
    StartedEvent,
    StepEvent,
    TokenEvent,
    is_terminal_event,
    parse_event,
)
from .run_manager import Run, RunManager, RunStatus
from .streaming import LangGraphBackend, QueueBackend, StreamingBackend

__version__ = "0.0.1"

__all__ = [
    # Event Models
    "BaseEvent",
    "StartedEvent",
    "ProgressEvent",
    "CheckpointEvent",
    "TokenEvent",
    "StepEvent",
    "CompleteEvent",
    "ErrorEvent",
    "HeartbeatEvent",
    "CancelledEvent",
    "is_terminal_event",
    "parse_event",
    # Core Classes
    "EventBus",
    "StreamContext",
    "EventsFilter",
    "RunManager",
    "Run",
    "RunStatus",
    # EventBus Backends
    "EventBackend",
    "InMemoryBackend",
    # Streaming Backends (for StreamContext)
    "StreamingBackend",
    "LangGraphBackend",
    "QueueBackend",
    # Context Access
    "get_current_context",
    "set_current_context",
    "context_scope",
]


# Lazy import for RedisBackend to avoid requiring redis dependency
def __getattr__(name: str):
    if name == "RedisBackend":
        from .backends.redis import RedisBackend

        return RedisBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
