"""
Dockrion Events Backends

Pluggable backend implementations for event storage and delivery.

Available Backends:
    - InMemoryBackend: For development and testing
    - RedisBackend: For production (requires redis extra)
"""

from .base import EventBackend
from .memory import InMemoryBackend

__all__ = [
    "EventBackend",
    "InMemoryBackend",
]


# Lazy import for RedisBackend
def __getattr__(name: str):
    if name == "RedisBackend":
        from .redis import RedisBackend

        return RedisBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
