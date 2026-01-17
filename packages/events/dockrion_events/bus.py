"""
Event Bus Abstraction

The EventBus provides a high-level interface for event routing and delivery.
It sits between the application layer (StreamContext, RunManager) and the
transport layer (backends).

Responsibilities:
    - Channel naming convention (run:{run_id})
    - Event serialization/deserialization
    - Publishing events to subscribers
    - Event storage for replay
    - Event retrieval for reconnection

Usage:
    from dockrion_events import EventBus, InMemoryBackend

    backend = InMemoryBackend()
    bus = EventBus(backend)

    # Publish an event
    await bus.publish("run-123", progress_event)

    # Subscribe to events
    async for event in bus.subscribe("run-123"):
        print(f"Received: {event.type}")

    # Get stored events (for replay)
    events = await bus.get_events("run-123", from_sequence=5)
"""

from typing import Any, AsyncIterator, Dict, List, Optional

from dockrion_common import get_logger

from .backends.base import EventBackend
from .models import BaseEvent, parse_event

logger = get_logger("events.bus")


def _channel_name(run_id: str) -> str:
    """Generate channel name for a run."""
    return f"run:{run_id}"


class EventBus:
    """
    High-level event routing and delivery.

    The EventBus wraps an EventBackend and provides:
    - Type-safe event handling with Pydantic models
    - Automatic channel naming
    - Combined publish + store operations
    - Event replay support

    Attributes:
        _backend: The underlying event backend
    """

    def __init__(self, backend: EventBackend):
        """
        Initialize the EventBus with a backend.

        Args:
            backend: EventBackend implementation (InMemory, Redis, etc.)
        """
        self._backend = backend
        logger.debug("EventBus initialized", backend=type(backend).__name__)

    @property
    def backend(self) -> EventBackend:
        """Get the underlying backend."""
        return self._backend

    async def publish(self, run_id: str, event: BaseEvent) -> None:
        """
        Publish an event for a run.

        This method:
        1. Converts the event to a dictionary
        2. Publishes to the channel for real-time delivery
        3. Stores the event for later retrieval

        Args:
            run_id: Run identifier
            event: Event to publish

        Example:
            >>> await bus.publish("run-123", ProgressEvent(
            ...     run_id="run-123",
            ...     step="parsing",
            ...     progress=0.5
            ... ))
        """
        channel = _channel_name(run_id)
        event_data = event.to_dict()

        # Publish for real-time delivery
        await self._backend.publish(channel, event_data)

        # Store for replay
        await self._backend.store_event(run_id, event_data)

        logger.debug(
            "Event published",
            run_id=run_id,
            event_type=event.type,
            sequence=event.sequence,
        )

    async def subscribe(
        self,
        run_id: str,
        from_sequence: int = 0,
        include_stored: bool = True,
    ) -> AsyncIterator[BaseEvent]:
        """
        Subscribe to events for a run.

        This method:
        1. Optionally retrieves and yields stored events (for replay)
        2. Then subscribes to live events

        Args:
            run_id: Run identifier to subscribe to
            from_sequence: Start from this sequence number (for replay)
            include_stored: Whether to replay stored events first

        Yields:
            Events as they are received (stored first, then live)

        Example:
            >>> async for event in bus.subscribe("run-123", from_sequence=5):
            ...     print(f"Event: {event.type} seq={event.sequence}")
        """
        channel = _channel_name(run_id)

        # First, yield stored events for replay
        if include_stored and from_sequence > 0:
            stored_events = await self.get_events(run_id, from_sequence)
            for event in stored_events:
                yield event
                logger.debug(
                    "Replayed stored event",
                    run_id=run_id,
                    event_type=event.type,
                    sequence=event.sequence,
                )

        # Then, subscribe to live events
        async for event_data in self._backend.subscribe(channel):
            try:
                event = parse_event(event_data)
                yield event
            except Exception as e:
                logger.warning(
                    "Failed to parse event",
                    run_id=run_id,
                    error=str(e),
                    event_data=event_data,
                )
                continue

    async def subscribe_raw(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to raw event dictionaries (no parsing).

        Useful when you need the raw event data without model conversion.

        Args:
            run_id: Run identifier to subscribe to

        Yields:
            Event dictionaries as received
        """
        channel = _channel_name(run_id)
        async for event_data in self._backend.subscribe(channel):
            yield event_data

    async def get_events(
        self,
        run_id: str,
        from_sequence: int = 0,
    ) -> List[BaseEvent]:
        """
        Retrieve stored events for a run.

        Used for event replay when a client reconnects.

        Args:
            run_id: Run identifier
            from_sequence: Minimum sequence number to retrieve

        Returns:
            List of events, ordered by sequence
        """
        event_dicts = await self._backend.get_events(run_id, from_sequence)
        events: List[BaseEvent] = []

        for event_data in event_dicts:
            try:
                event = parse_event(event_data)
                events.append(event)
            except Exception as e:
                logger.warning(
                    "Failed to parse stored event",
                    run_id=run_id,
                    error=str(e),
                    event_data=event_data,
                )
                continue

        return events

    async def get_events_raw(
        self,
        run_id: str,
        from_sequence: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve raw event dictionaries for a run.

        Args:
            run_id: Run identifier
            from_sequence: Minimum sequence number to retrieve

        Returns:
            List of event dictionaries, ordered by sequence
        """
        return await self._backend.get_events(run_id, from_sequence)

    async def publish_raw(self, run_id: str, event_data: Dict[str, Any]) -> None:
        """
        Publish a raw event dictionary.

        Useful when working with events that don't have a model.

        Args:
            run_id: Run identifier
            event_data: Event dictionary to publish
        """
        channel = _channel_name(run_id)
        await self._backend.publish(channel, event_data)
        await self._backend.store_event(run_id, event_data)

    async def close(self) -> None:
        """Close the event bus and underlying backend."""
        await self._backend.close()
        logger.info("EventBus closed")

    async def clear_run(self, run_id: str) -> None:
        """
        Clear stored events for a run.

        Args:
            run_id: Run identifier to clear
        """
        if hasattr(self._backend, "clear_run"):
            await self._backend.clear_run(run_id)


class EventBusFactory:
    """
    Factory for creating EventBus instances with different backends.

    Usage:
        bus = await EventBusFactory.create("memory")
        bus = await EventBusFactory.create("redis", url="redis://localhost:6379")
    """

    @staticmethod
    async def create(
        backend_type: str = "memory",
        **kwargs: Any,
    ) -> EventBus:
        """
        Create an EventBus with the specified backend.

        Args:
            backend_type: "memory" or "redis"
            **kwargs: Backend-specific configuration

        Returns:
            Configured EventBus instance

        Raises:
            ValueError: If backend_type is unknown
        """
        if backend_type == "memory":
            from .backends.memory import InMemoryBackend

            backend = InMemoryBackend(max_events_per_run=kwargs.get("max_events_per_run", 1000))
            return EventBus(backend)

        elif backend_type == "redis":
            try:
                from .backends.redis import RedisBackend
            except ImportError as e:
                raise ImportError(
                    "Redis backend requires 'redis' extra. "
                    "Install with: pip install dockrion-events[redis]"
                ) from e

            backend = RedisBackend(
                url=kwargs.get("url", "redis://localhost:6379"),
                stream_ttl_seconds=kwargs.get("stream_ttl_seconds", 3600),
                max_events_per_run=kwargs.get("max_events_per_run", 1000),
                connection_pool_size=kwargs.get("connection_pool_size", 10),
            )
            return EventBus(backend)

        else:
            raise ValueError(f"Unknown backend type: {backend_type}")


# Convenience function
async def create_event_bus(
    backend_type: str = "memory",
    **kwargs: Any,
) -> EventBus:
    """
    Create an EventBus with the specified backend.

    Convenience function that delegates to EventBusFactory.

    Args:
        backend_type: "memory" or "redis"
        **kwargs: Backend-specific configuration

    Returns:
        Configured EventBus instance
    """
    return await EventBusFactory.create(backend_type, **kwargs)
