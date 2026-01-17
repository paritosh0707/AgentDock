"""
Queue-based streaming backend (fallback).

Used when native framework backend is unavailable or fails.
Events are queued and drained by the adapter after each step.
"""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..models import BaseEvent


class QueueBackend:
    """
    Queue-based backend for event storage and draining.

    Events are stored internally and drained by the adapter
    after each execution step via drain().
    """

    def __init__(self):
        self._queue: List["BaseEvent"] = []

    @property
    def name(self) -> str:
        return "queue"

    def emit(self, event: "BaseEvent") -> bool:
        """Queue the event for later draining."""
        self._queue.append(event)
        return True

    def is_available(self) -> bool:
        """Queue backend is always available."""
        return True

    def drain(self) -> List["BaseEvent"]:
        """Drain all queued events. Returns list and clears queue."""
        events = self._queue.copy()
        self._queue.clear()
        return events

    def __len__(self) -> int:
        return len(self._queue)
