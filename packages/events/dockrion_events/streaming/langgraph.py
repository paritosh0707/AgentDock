"""
Native LangGraph streaming backend.

Uses LangGraph's get_stream_writer() to emit events directly to the stream,
providing accurate timing and avoiding queue overhead.
"""

from typing import TYPE_CHECKING, Any, Optional

from dockrion_common.logger import get_logger

if TYPE_CHECKING:
    from ..models import BaseEvent

logger = get_logger("events.streaming.langgraph")


class LangGraphBackend:
    """
    Native LangGraph streaming backend.

    Emits events via LangGraph's stream writer. Events appear in
    the stream as ("custom", (event_type, event_data)) tuples.
    """

    @property
    def name(self) -> str:
        return "langgraph"

    def _get_writer(self) -> Optional[Any]:
        """Get LangGraph's stream writer from current context."""
        try:
            from langgraph.config import get_stream_writer

            return get_stream_writer()
        except ImportError:
            return None
        except Exception as e:
            logger.debug(f"Failed to get stream writer: {e}")
            return None

    def is_available(self) -> bool:
        """Check if LangGraph stream writer is available."""
        return self._get_writer() is not None

    def emit(self, event: "BaseEvent") -> bool:
        """
        Emit event via LangGraph's native stream writer.

        Emits as tuple: (event_type, event_data)
        - Known events: ("progress", {"step": ..., "progress": ...})
        - Custom events: ("custom:name", {"data": ...})

        Returns:
            True if emitted, False if writer unavailable
        """
        writer = self._get_writer()
        if writer is None:
            return False

        try:
            # Build event type string
            event_type = event.type
            if event_type == "custom" and hasattr(event, "name"):
                event_type = f"custom:{event.name}"

            # Build event data (exclude type, it's in the tuple)
            event_data = event.model_dump(exclude={"type"})

            # Emit to LangGraph stream
            writer((event_type, event_data))
            logger.debug(f"Emitted via LangGraph native: {event_type}")
            return True

        except Exception as e:
            logger.debug(f"Failed to emit via LangGraph: {e}")
            return False
