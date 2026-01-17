"""
In-Memory Event Backend

Development and testing backend that stores events in memory.
Uses asyncio.Queue for pub/sub functionality.

Characteristics:
    - Events stored in process memory
    - Lost on restart
    - Single instance only
    - No event replay after disconnect (limited)
    - No external dependencies

Usage:
    from dockrion_events.backends import InMemoryBackend

    backend = InMemoryBackend()
    await backend.publish("run:abc123", {"type": "progress", ...})
"""

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, Dict, List, Optional

from dockrion_common import get_logger

logger = get_logger("events.backend.memory")


class InMemoryBackend:
    """
    In-memory event backend for development and testing.

    Uses asyncio.Queue for real-time event delivery and a dict
    for event storage. Suitable for single-instance deployments
    and testing scenarios.

    Attributes:
        _channels: Dict mapping channel names to lists of subscriber queues
        _events: Dict mapping run_ids to lists of stored events
        _max_events_per_run: Maximum events to store per run
    """

    def __init__(self, max_events_per_run: int = 1000):
        """
        Initialize the in-memory backend.

        Args:
            max_events_per_run: Maximum events to retain per run (default: 1000)
        """
        self._channels: Dict[str, List[asyncio.Queue[Optional[Dict[str, Any]]]]] = defaultdict(list)
        self._events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._max_events_per_run = max_events_per_run
        self._lock = asyncio.Lock()
        self._closed = False

        logger.debug(
            "InMemoryBackend initialized",
            max_events_per_run=max_events_per_run,
        )

    async def publish(self, channel: str, event: Dict[str, Any]) -> None:
        """
        Publish an event to a channel.

        Delivers the event to all active subscribers on the channel.

        Args:
            channel: Channel name (e.g., "run:abc123")
            event: Event data dictionary
        """
        if self._closed:
            logger.warning("Publish called on closed backend", channel=channel)
            return

        async with self._lock:
            subscribers = self._channels.get(channel, [])
            for queue in subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(
                        "Subscriber queue full, dropping event",
                        channel=channel,
                        event_type=event.get("type"),
                    )

        logger.debug(
            "Event published",
            channel=channel,
            event_type=event.get("type"),
            subscribers=len(subscribers),
        )

    async def subscribe(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to events on a channel.

        Creates a new queue for this subscriber and yields events
        as they are published. Cleans up on cancellation.

        Args:
            channel: Channel name to subscribe to

        Yields:
            Event dictionaries as they are published
        """
        if self._closed:
            logger.warning("Subscribe called on closed backend", channel=channel)
            return

        queue: asyncio.Queue[Optional[Dict[str, Any]]] = asyncio.Queue(maxsize=100)

        async with self._lock:
            self._channels[channel].append(queue)

        logger.debug(
            "Subscriber added",
            channel=channel,
            total_subscribers=len(self._channels[channel]),
        )

        try:
            while not self._closed:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if event is None:
                        # Shutdown signal
                        break
                    yield event
                except asyncio.TimeoutError:
                    # Continue waiting - allows checking _closed flag
                    continue
        finally:
            # Cleanup: remove this subscriber's queue
            async with self._lock:
                if channel in self._channels and queue in self._channels[channel]:
                    self._channels[channel].remove(queue)
                    if not self._channels[channel]:
                        del self._channels[channel]

            logger.debug("Subscriber removed", channel=channel)

    async def store_event(self, run_id: str, event: Dict[str, Any]) -> None:
        """
        Store an event for later retrieval.

        Maintains ordering by sequence number and limits total events.

        Args:
            run_id: Run identifier
            event: Event data dictionary
        """
        if self._closed:
            return

        async with self._lock:
            events = self._events[run_id]
            events.append(event)

            # Trim to max events
            if len(events) > self._max_events_per_run:
                self._events[run_id] = events[-self._max_events_per_run :]

        logger.debug(
            "Event stored",
            run_id=run_id,
            event_type=event.get("type"),
            sequence=event.get("sequence"),
            total_events=len(self._events[run_id]),
        )

    async def get_events(self, run_id: str, from_sequence: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve stored events for a run.

        Args:
            run_id: Run identifier
            from_sequence: Minimum sequence number to retrieve

        Returns:
            List of event dictionaries, ordered by sequence
        """
        async with self._lock:
            events = self._events.get(run_id, [])
            filtered = [e for e in events if e.get("sequence", 0) >= from_sequence]

        logger.debug(
            "Events retrieved",
            run_id=run_id,
            from_sequence=from_sequence,
            total_events=len(events),
            filtered_events=len(filtered),
        )

        return sorted(filtered, key=lambda e: e.get("sequence", 0))

    async def close(self) -> None:
        """
        Close the backend and notify all subscribers.
        """
        self._closed = True

        async with self._lock:
            # Send shutdown signal to all subscribers
            for _channel, subscribers in self._channels.items():
                for queue in subscribers:
                    try:
                        queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass

            self._channels.clear()

        logger.info("InMemoryBackend closed")

    async def clear_run(self, run_id: str) -> None:
        """
        Clear stored events for a run.

        Args:
            run_id: Run identifier to clear
        """
        async with self._lock:
            if run_id in self._events:
                del self._events[run_id]

        logger.debug("Run events cleared", run_id=run_id)

    def get_subscriber_count(self, channel: str) -> int:
        """
        Get the number of subscribers on a channel.

        Args:
            channel: Channel name

        Returns:
            Number of active subscribers
        """
        return len(self._channels.get(channel, []))

    def get_event_count(self, run_id: str) -> int:
        """
        Get the number of stored events for a run.

        Args:
            run_id: Run identifier

        Returns:
            Number of stored events
        """
        return len(self._events.get(run_id, []))
