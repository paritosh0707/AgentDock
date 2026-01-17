"""
Event Backend Protocol

Defines the interface that all event backends must implement.
Using Protocol (PEP 544) provides structural subtyping without requiring inheritance.

Backends are responsible for:
    - Publishing events to channels (real-time delivery)
    - Storing events for later retrieval (durability)
    - Subscribing to event channels
    - Retrieving stored events (replay)

Available Implementations:
    - InMemoryBackend: For development and testing
    - RedisBackend: For production with durability

Usage:
    from dockrion_events.backends import EventBackend, InMemoryBackend

    # Create backend
    backend: EventBackend = InMemoryBackend()

    # Use with EventBus
    bus = EventBus(backend)
"""

from typing import Any, AsyncIterator, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class EventBackend(Protocol):
    """
    Protocol defining the interface for event backends.

    All backend implementations must provide these methods to ensure
    uniform interaction regardless of the underlying infrastructure.

    The channel naming convention is:
        run:{run_id} - Channel for a specific run's events
    """

    async def publish(self, channel: str, event: Dict[str, Any]) -> None:
        """
        Publish an event to a channel for real-time delivery.

        This method delivers the event to all active subscribers immediately.
        The event should also be stored via store_event() for durability.

        Args:
            channel: Channel name (e.g., "run:abc123")
            event: Event data dictionary

        Example:
            >>> await backend.publish("run:abc123", {"type": "progress", ...})
        """
        ...

    def subscribe(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to events on a channel.

        Returns an async iterator that yields events as they are published.
        The iterator should handle cleanup on cancellation.

        Args:
            channel: Channel name to subscribe to

        Yields:
            Event dictionaries as they are published

        Example:
            >>> async for event in backend.subscribe("run:abc123"):
            ...     print(f"Received: {event['type']}")
        """
        ...

    async def store_event(self, run_id: str, event: Dict[str, Any]) -> None:
        """
        Store an event for later retrieval.

        Events are stored with their sequence number for ordering.
        This enables event replay for reconnecting clients.

        Args:
            run_id: Run identifier
            event: Event data dictionary (must include 'sequence' field)

        Example:
            >>> await backend.store_event("abc123", {"type": "progress", "sequence": 5, ...})
        """
        ...

    async def get_events(self, run_id: str, from_sequence: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve stored events for a run.

        Used for event replay when a client reconnects.
        Returns events with sequence >= from_sequence.

        Args:
            run_id: Run identifier
            from_sequence: Minimum sequence number to retrieve

        Returns:
            List of event dictionaries, ordered by sequence

        Example:
            >>> events = await backend.get_events("abc123", from_sequence=5)
            >>> print(f"Retrieved {len(events)} events")
        """
        ...

    async def close(self) -> None:
        """
        Close the backend and release resources.

        Should be called when the backend is no longer needed.
        This is optional - not all backends require cleanup.
        """
        ...

    async def clear_run(self, run_id: str) -> None:
        """
        Clear stored events for a run.

        This is an optional method for cleanup. Implementations should
        remove all stored events associated with the run ID.

        Args:
            run_id: Run identifier to clear

        Example:
            >>> await backend.clear_run("abc123")
        """
        ...


class BackendError(Exception):
    """Base exception for backend errors."""

    def __init__(self, message: str, backend: str = "unknown"):
        self.message = message
        self.backend = backend
        super().__init__(f"[{backend}] {message}")


class BackendConnectionError(BackendError):
    """Raised when backend connection fails."""

    pass


class BackendPublishError(BackendError):
    """Raised when event publishing fails."""

    pass


class BackendSubscribeError(BackendError):
    """Raised when subscription fails."""

    pass
