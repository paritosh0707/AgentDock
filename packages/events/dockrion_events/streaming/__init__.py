"""
Streaming backends for StreamContext event emission.

These backends determine how events are emitted from StreamContext:
- LangGraphBackend: Native LangGraph streaming via get_stream_writer()
- QueueBackend: Queue-based fallback for adapter draining

Note: This is separate from events.backends which handles EventBus storage.
"""

from .base import StreamingBackend
from .langgraph import LangGraphBackend
from .queue import QueueBackend

__all__ = [
    "StreamingBackend",
    "LangGraphBackend",
    "QueueBackend",
]
