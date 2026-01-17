"""
StreamContext API

The StreamContext is the user-facing interface for emitting events from
agent code. It provides methods for emitting different types of events
(progress, checkpoint, token, step, custom) and handles sequence numbering
automatically.

Two ways to access the context:

1. **Direct Parameter**: Context passed as parameter to handler
   ```python
   def my_handler(payload: dict, context: StreamContext) -> dict:
       context.emit_progress("processing", 0.5)
       return {"result": "done"}
   ```

2. **Thread-Local Access**: Via get_current_context()
   ```python
   from dockrion_events import get_current_context

   def my_node(state):
       context = get_current_context()
       if context:
           context.emit_step("my_node")
       return state
   ```

Two operation modes:

1. **EventBus Mode** (Pattern B - /runs endpoint):
   Events are published directly to the EventBus for async delivery.
   ```python
   context = StreamContext(run_id="run-123", bus=bus)
   ```

2. **Queue Mode** (Pattern A - /invoke/stream endpoint):
   Events are queued internally for synchronous draining by the adapter.
   ```python
   context = StreamContext(run_id="run-123", bus=bus, queue_mode=True)
   events = context.drain_queued_events()  # Get and clear queued events
   ```

Event Filtering:

Events can be filtered based on Dockfile configuration using EventsFilter.
```python
from dockrion_events import EventsFilter

filter = EventsFilter(["token", "step"])  # Only token and step events
context = StreamContext(run_id="run-123", bus=bus, events_filter=filter)

# This will emit (token is allowed)
context.sync_emit_token("Hello")

# This will be silently skipped (progress not allowed)
context.sync_emit_progress("step", 0.5)
```

Note: Mandatory events (started, complete, error, cancelled) are ALWAYS
emitted regardless of filter configuration.

Usage:
    from dockrion_events import StreamContext, EventBus

    bus = EventBus(backend)
    context = StreamContext(run_id="run-123", bus=bus)

    # Emit events
    await context.emit_progress("parsing", 0.5, "Halfway done")
    await context.checkpoint("intermediate", {"data": 123})
    await context.emit_token("Hello")
    await context.emit_step("process_node", duration_ms=150)
    await context.emit("custom_event", {"key": "value"})
"""

from __future__ import annotations

import asyncio
import queue
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from dockrion_common import get_logger

from .bus import EventBus
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
)

if TYPE_CHECKING:
    from .filter import EventsFilter
    from .streaming import StreamingBackend

logger = get_logger("events.context")

# Thread-local storage for StreamContext
_current_context: ContextVar[Optional["StreamContext"]] = ContextVar("stream_context", default=None)


def get_current_context() -> Optional["StreamContext"]:
    """
    Get the current StreamContext from thread-local storage.

    Returns None if no context is set for the current thread/task.

    Returns:
        StreamContext if set, None otherwise

    Example:
        >>> context = get_current_context()
        >>> if context:
        ...     context.emit_progress("step", 0.5)
    """
    return _current_context.get()


def set_current_context(context: Optional["StreamContext"]) -> None:
    """
    Set the StreamContext for the current thread/task.

    Args:
        context: StreamContext to set, or None to clear

    Example:
        >>> set_current_context(my_context)
        >>> # ... do work ...
        >>> set_current_context(None)  # cleanup
    """
    _current_context.set(context)


@contextmanager
def context_scope(context: Optional["StreamContext"]):
    """
    Context manager for setting StreamContext within a scope.

    Automatically restores the previous context on exit.

    Args:
        context: StreamContext to set for the duration

    Example:
        >>> with context_scope(my_context):
        ...     # get_current_context() returns my_context
        ...     do_work()
        >>> # get_current_context() returns previous value
    """
    previous = _current_context.get()
    _current_context.set(context)
    try:
        yield context
    finally:
        _current_context.set(previous)


class StreamContext:
    """
    User-facing API for emitting events during agent execution.

    The StreamContext provides type-safe methods for emitting different
    kinds of events. It handles:
    - Automatic sequence numbering
    - Event creation with proper run_id
    - Publishing to the EventBus (Pattern B) or internal queue (Pattern A)
    - Event filtering based on Dockfile configuration
    - Both sync and async usage

    Operation Modes:
    - EventBus Mode (queue_mode=False): Events published directly to EventBus
    - Queue Mode (queue_mode=True): Events stored in internal queue for draining

    Attributes:
        run_id: The current run identifier
        _bus: The EventBus for publishing events (may be None in queue mode)
        _sequence: Current sequence counter
        _agent_name: Optional agent name for context
        _framework: Optional framework name for context
        _lock: Thread lock for sequence counter
        _queue_mode: Whether to queue events instead of publishing
        _events_filter: Optional filter for allowed events
        _event_queue: Internal queue for Pattern A mode
    """

    def __init__(
        self,
        run_id: str,
        bus: Optional[EventBus] = None,
        agent_name: Optional[str] = None,
        framework: Optional[str] = None,
        queue_mode: bool = False,
        events_filter: Optional["EventsFilter"] = None,
        streaming_backend: Optional["StreamingBackend"] = None,
    ):
        """
        Initialize a StreamContext.

        Args:
            run_id: Run identifier for all events
            bus: EventBus for publishing events (required unless queue_mode=True)
            agent_name: Optional agent name (included in started event)
            framework: Optional framework name (included in started event)
            queue_mode: If True, queue events instead of publishing to bus
            events_filter: Optional filter to control which events are emitted
            streaming_backend: Optional native streaming backend (e.g., LangGraphBackend)

        Raises:
            ValueError: If bus is None and queue_mode is False
        """
        if not queue_mode and bus is None:
            raise ValueError("EventBus required when queue_mode is False")

        self._run_id = run_id
        self._bus = bus
        self._sequence = 0
        self._agent_name = agent_name
        self._framework = framework
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

        # Queue mode for Pattern A (direct streaming)
        self._queue_mode = queue_mode
        self._event_queue: queue.Queue[BaseEvent] = queue.Queue()

        # Event filtering
        self._events_filter = events_filter

        # Native streaming backend (e.g., LangGraphBackend)
        self._streaming_backend = streaming_backend

        logger.debug(
            "StreamContext created",
            run_id=run_id,
            agent_name=agent_name,
            framework=framework,
            queue_mode=queue_mode,
            has_filter=events_filter is not None,
            streaming_backend=streaming_backend.name if streaming_backend else None,
        )

    @property
    def run_id(self) -> str:
        """Get the current run identifier."""
        return self._run_id

    @property
    def queue_mode(self) -> bool:
        """Check if context is in queue mode."""
        return self._queue_mode

    @property
    def events_filter(self) -> Optional["EventsFilter"]:
        """Get the events filter (if any)."""
        return self._events_filter

    @property
    def streaming_backend(self) -> Optional["StreamingBackend"]:
        """Get the streaming backend (if any)."""
        return self._streaming_backend

    def _next_sequence(self) -> int:
        """Get the next sequence number (thread-safe)."""
        with self._lock:
            self._sequence += 1
            return self._sequence

    def _is_event_allowed(
        self,
        event_type: str,
        custom_event_name: Optional[str] = None,
    ) -> bool:
        """
        Check if an event should be emitted based on filter.

        Args:
            event_type: The type of event (e.g., "token", "step", "progress")
            custom_event_name: For custom events, the specific event name

        Returns:
            True if event should be emitted, False to skip
        """
        if self._events_filter is None:
            return True
        return self._events_filter.is_allowed(event_type, custom_event_name)

    def _enqueue_event(self, event: BaseEvent) -> None:
        """Add event to the internal queue (for queue mode)."""
        self._event_queue.put(event)

    def _emit_via_backend(self, event: BaseEvent) -> bool:
        """
        Emit event via native streaming backend.

        Tries native backend first, falls back to queue if unavailable.

        Returns:
            True if emitted via backend, False if queued as fallback
        """
        if self._streaming_backend is not None:
            try:
                if self._streaming_backend.emit(event):
                    logger.debug(
                        f"Event emitted via {self._streaming_backend.name}",
                        event_type=event.type,
                        run_id=self._run_id,
                    )
                    return True
            except Exception as e:
                logger.debug(f"Backend emit failed, falling back to queue: {e}")

        # Fallback to queue
        self._enqueue_event(event)
        return False

    async def _publish(self, event: BaseEvent) -> None:
        """Publish an event to the bus or queue."""
        if self._queue_mode:
            # In queue mode, try native backend first
            if self._streaming_backend is not None:
                self._emit_via_backend(event)
            else:
                self._enqueue_event(event)
        elif self._bus is not None:
            await self._bus.publish(self._run_id, event)

    def _sync_publish(self, event: BaseEvent) -> None:
        """Synchronously publish an event (runs event loop if needed)."""
        if self._queue_mode:
            # In queue mode, try native backend first
            if self._streaming_backend is not None:
                self._emit_via_backend(event)
            else:
                self._enqueue_event(event)
        elif self._bus is not None:
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, schedule the coroutine
                asyncio.create_task(self._bus.publish(self._run_id, event))
            except RuntimeError:
                # No running loop, create one
                asyncio.run(self._bus.publish(self._run_id, event))

    def drain_queued_events(self) -> List[BaseEvent]:
        """
        Drain all events from the internal queue.

        This is used in Pattern A (direct streaming) where the adapter
        collects events emitted during agent execution and includes
        them in the SSE stream.

        Returns:
            List of events in order they were emitted

        Example:
            >>> context = StreamContext(run_id="123", queue_mode=True)
            >>> context.sync_emit_token("Hello")
            >>> context.sync_emit_token(" world")
            >>> events = context.drain_queued_events()
            >>> len(events)
            2
            >>> context.drain_queued_events()  # Queue is now empty
            []
        """
        events = []
        while True:
            try:
                event = self._event_queue.get_nowait()
                events.append(event)
            except queue.Empty:
                break
        return events

    def has_queued_events(self) -> bool:
        """Check if there are events in the queue."""
        return not self._event_queue.empty()

    def queue_size(self) -> int:
        """Get the approximate number of queued events."""
        return self._event_queue.qsize()

    # =========================================================================
    # ASYNC EMIT METHODS
    # =========================================================================

    async def emit_started(
        self,
        agent_name: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> StartedEvent:
        """
        Emit a started event.

        Called automatically by the runtime when a run begins.

        Args:
            agent_name: Agent name (overrides constructor value)
            framework: Framework name (overrides constructor value)

        Returns:
            The emitted StartedEvent
        """
        event = StartedEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            agent_name=agent_name or self._agent_name,
            framework=framework or self._framework,
        )
        await self._publish(event)
        logger.debug("Emitted started event", run_id=self._run_id)
        return event

    async def emit_progress(
        self,
        step: str,
        progress: float,
        message: Optional[str] = None,
    ) -> Optional[ProgressEvent]:
        """
        Emit a progress event.

        Args:
            step: Current step/phase name
            progress: Progress percentage (0.0 to 1.0)
            message: Optional human-readable message

        Returns:
            The emitted ProgressEvent, or None if filtered out

        Example:
            >>> await context.emit_progress("parsing", 0.5, "Parsing document...")
        """
        if not self._is_event_allowed("progress"):
            return None

        event = ProgressEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            step=step,
            progress=progress,
            message=message,
        )
        await self._publish(event)
        logger.debug(
            "Emitted progress event",
            run_id=self._run_id,
            step=step,
            progress=progress,
        )
        return event

    async def checkpoint(
        self,
        name: str,
        data: Dict[str, Any],
    ) -> Optional[CheckpointEvent]:
        """
        Emit a checkpoint event with intermediate data.

        Args:
            name: Checkpoint identifier
            data: Data to include in checkpoint

        Returns:
            The emitted CheckpointEvent, or None if filtered out

        Example:
            >>> await context.checkpoint("parsed_doc", {"fields": 15, "confidence": 0.9})
        """
        if not self._is_event_allowed("checkpoint"):
            return None

        event = CheckpointEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            name=name,
            data=data,
        )
        await self._publish(event)
        logger.debug(
            "Emitted checkpoint event",
            run_id=self._run_id,
            name=name,
        )
        return event

    async def emit_token(
        self,
        content: str,
        finish_reason: Optional[str] = None,
    ) -> Optional[TokenEvent]:
        """
        Emit an LLM token event.

        Args:
            content: Token text content
            finish_reason: Why generation stopped (if final)

        Returns:
            The emitted TokenEvent, or None if filtered out

        Example:
            >>> await context.emit_token("Hello")
            >>> await context.emit_token(" world!", finish_reason="stop")
        """
        if not self._is_event_allowed("token"):
            return None

        event = TokenEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            content=content,
            finish_reason=finish_reason,
        )
        await self._publish(event)
        return event

    async def emit_step(
        self,
        node_name: str,
        duration_ms: Optional[int] = None,
        input_keys: Optional[List[str]] = None,
        output_keys: Optional[List[str]] = None,
    ) -> Optional[StepEvent]:
        """
        Emit a step completion event.

        Args:
            node_name: Name of completed step/node
            duration_ms: Step execution time in milliseconds
            input_keys: Keys present in step input
            output_keys: Keys present in step output

        Returns:
            The emitted StepEvent, or None if filtered out

        Example:
            >>> await context.emit_step("extract_fields", duration_ms=150, output_keys=["fields"])
        """
        if not self._is_event_allowed("step"):
            return None

        event = StepEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            node_name=node_name,
            duration_ms=duration_ms,
            input_keys=input_keys or [],
            output_keys=output_keys or [],
        )
        await self._publish(event)
        logger.debug(
            "Emitted step event",
            run_id=self._run_id,
            node_name=node_name,
            duration_ms=duration_ms,
        )
        return event

    async def emit_complete(
        self,
        output: Dict[str, Any],
        latency_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CompleteEvent:
        """
        Emit a completion event.

        Called automatically by the runtime on successful completion.

        Args:
            output: Final agent output
            latency_seconds: Total execution time
            metadata: Additional metadata

        Returns:
            The emitted CompleteEvent
        """
        event = CompleteEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            output=output,
            latency_seconds=latency_seconds,
            metadata=metadata or {},
        )
        await self._publish(event)
        logger.debug(
            "Emitted complete event",
            run_id=self._run_id,
            latency_seconds=latency_seconds,
        )
        return event

    async def emit_error(
        self,
        error: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorEvent:
        """
        Emit an error event.

        Called automatically by the runtime on failure.

        Args:
            error: Error message
            code: Error code
            details: Additional error context

        Returns:
            The emitted ErrorEvent
        """
        event = ErrorEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            error=error,
            code=code,
            details=details,
        )
        await self._publish(event)
        logger.debug(
            "Emitted error event",
            run_id=self._run_id,
            code=code,
        )
        return event

    async def emit_heartbeat(self) -> Optional[HeartbeatEvent]:
        """
        Emit a heartbeat event.

        Called automatically by the runtime at configured intervals.

        Returns:
            The emitted HeartbeatEvent, or None if filtered out
        """
        if not self._is_event_allowed("heartbeat"):
            return None

        event = HeartbeatEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
        )
        await self._publish(event)
        return event

    async def emit_cancelled(
        self,
        reason: Optional[str] = None,
    ) -> CancelledEvent:
        """
        Emit a cancellation event.

        Called by the runtime when a run is cancelled.

        Args:
            reason: Reason for cancellation

        Returns:
            The emitted CancelledEvent
        """
        event = CancelledEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            reason=reason,
        )
        await self._publish(event)
        logger.debug(
            "Emitted cancelled event",
            run_id=self._run_id,
            reason=reason,
        )
        return event

    async def emit(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> Optional[BaseEvent]:
        """
        Emit a custom event with arbitrary data.

        Args:
            event_type: Custom event type name
            data: Event payload

        Returns:
            The emitted event, or None if filtered out

        Example:
            >>> await context.emit("fraud_check", {"passed": True, "score": 0.02})
        """
        if not self._is_event_allowed("custom", custom_event_name=event_type):
            return None

        event = BaseEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            type=event_type,
            **data,
        )
        await self._publish(event)
        logger.debug(
            "Emitted custom event",
            run_id=self._run_id,
            event_type=event_type,
        )
        return event

    # =========================================================================
    # SYNC EMIT METHODS (for non-async code)
    # =========================================================================

    def sync_emit_progress(
        self,
        step: str,
        progress: float,
        message: Optional[str] = None,
    ) -> bool:
        """
        Synchronously emit a progress event.

        Use this in synchronous handler code.

        Args:
            step: Current step/phase name
            progress: Progress percentage (0.0 to 1.0)
            message: Optional human-readable message

        Returns:
            True if event was emitted, False if filtered out
        """
        if not self._is_event_allowed("progress"):
            return False

        event = ProgressEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            step=step,
            progress=progress,
            message=message,
        )
        self._sync_publish(event)
        return True

    def sync_checkpoint(
        self,
        name: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Synchronously emit a checkpoint event.

        Args:
            name: Checkpoint identifier
            data: Data to include in checkpoint

        Returns:
            True if event was emitted, False if filtered out
        """
        if not self._is_event_allowed("checkpoint"):
            return False

        event = CheckpointEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            name=name,
            data=data,
        )
        self._sync_publish(event)
        return True

    def sync_emit_token(
        self,
        content: str,
        finish_reason: Optional[str] = None,
    ) -> bool:
        """
        Synchronously emit a token event.

        Args:
            content: Token text content
            finish_reason: Why generation stopped (if final)

        Returns:
            True if event was emitted, False if filtered out
        """
        if not self._is_event_allowed("token"):
            return False

        event = TokenEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            content=content,
            finish_reason=finish_reason,
        )
        self._sync_publish(event)
        return True

    def sync_emit_step(
        self,
        node_name: str,
        duration_ms: Optional[int] = None,
        input_keys: Optional[List[str]] = None,
        output_keys: Optional[List[str]] = None,
    ) -> bool:
        """
        Synchronously emit a step event.

        Args:
            node_name: Name of completed step/node
            duration_ms: Step execution time in milliseconds
            input_keys: Keys present in step input
            output_keys: Keys present in step output

        Returns:
            True if event was emitted, False if filtered out
        """
        if not self._is_event_allowed("step"):
            return False

        event = StepEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            node_name=node_name,
            duration_ms=duration_ms,
            input_keys=input_keys or [],
            output_keys=output_keys or [],
        )
        self._sync_publish(event)
        return True

    def sync_emit(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Synchronously emit a custom event.

        Args:
            event_type: Custom event type name
            data: Event payload

        Returns:
            True if event was emitted, False if filtered out
        """
        if not self._is_event_allowed("custom", custom_event_name=event_type):
            return False

        event = BaseEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
            type=event_type,
            **data,
        )
        self._sync_publish(event)
        return True

    def sync_emit_heartbeat(self) -> bool:
        """
        Synchronously emit a heartbeat event.

        Returns:
            True if event was emitted, False if filtered out
        """
        if not self._is_event_allowed("heartbeat"):
            return False

        event = HeartbeatEvent(
            run_id=self._run_id,
            sequence=self._next_sequence(),
        )
        self._sync_publish(event)
        return True
