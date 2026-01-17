"""
Streaming backend protocol for StreamContext event emission.

This defines the interface for backends that handle event emission
from user code (e.g., context.sync_emit_progress()).
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..models import BaseEvent


@runtime_checkable
class StreamingBackend(Protocol):
    """
    Protocol for streaming backends.

    Backends emit events from StreamContext to the output stream:
    - LangGraphBackend: Uses native get_stream_writer()
    - QueueBackend: Queues for adapter draining (fallback)
    """

    @property
    def name(self) -> str:
        """Backend identifier for logging."""
        ...

    def emit(self, event: "BaseEvent") -> bool:
        """
        Emit an event.

        Returns:
            True if emitted successfully
            False if unavailable (caller should fallback)
        """
        ...

    def is_available(self) -> bool:
        """Check if backend is currently available."""
        ...
