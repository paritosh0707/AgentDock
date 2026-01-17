"""
Redis Event Backend

Production backend using Redis Pub/Sub for real-time delivery
and Redis Streams for event persistence and replay.

Features:
    - Real-time event delivery via Pub/Sub
    - Event persistence in Redis Streams
    - Event replay for reconnecting clients
    - Automatic event expiration (TTL)
    - Connection pooling

Requires:
    pip install redis>=5.0.0

Usage:
    from dockrion_events.backends.redis import RedisBackend

    backend = RedisBackend(
        url="redis://localhost:6379",
        stream_ttl_seconds=3600,
        max_events_per_run=1000,
    )

    await backend.publish("run:abc123", {"type": "progress", ...})
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict, List, Optional

from dockrion_common import get_logger

from .base import BackendConnectionError, BackendPublishError, BackendSubscribeError

logger = get_logger("events.backend.redis")

# Runtime imports - try to import redis, gracefully handle if not installed
# These imports are optional - redis is only required when using RedisBackend
REDIS_AVAILABLE = False
aioredis: Any = None
RedisConnectionError: type[Exception] = Exception
RedisError: type[Exception] = Exception

try:
    import redis.asyncio as aioredis  # type: ignore[import-not-found]  # noqa: F811
    from redis.exceptions import (
        ConnectionError as RedisConnectionError,  # type: ignore[import-not-found]  # noqa: F811
    )
    from redis.exceptions import RedisError  # type: ignore[import-not-found]  # noqa: F811

    REDIS_AVAILABLE = True
except ImportError:
    pass


def _stream_key(run_id: str) -> str:
    """Generate Redis Streams key for a run."""
    return f"stream:run:{run_id}"


def _channel_key(channel: str) -> str:
    """Generate Pub/Sub channel key."""
    return f"events:{channel}"


class RedisBackend:
    """
    Redis-based event backend for production deployments.

    Uses both Redis Pub/Sub and Streams:
    - Pub/Sub: Real-time event delivery to active subscribers
    - Streams: Durable storage for event replay

    Attributes:
        _url: Redis connection URL
        _redis: Redis connection pool
        _stream_ttl: Event retention time in seconds
        _max_events: Maximum events per run
        _pool_size: Connection pool size
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        stream_ttl_seconds: int = 3600,
        max_events_per_run: int = 1000,
        connection_pool_size: int = 10,
    ):
        """
        Initialize the Redis backend.

        Args:
            url: Redis connection URL (redis://host:port/db)
            stream_ttl_seconds: Event retention time (default: 1 hour)
            max_events_per_run: Max events to retain per run
            connection_pool_size: Connection pool size

        Raises:
            ImportError: If redis package is not installed
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis backend requires 'redis' package. "
                "Install with: pip install dockrion-events[redis]"
            )

        self._url = url
        self._stream_ttl = stream_ttl_seconds
        self._max_events = max_events_per_run
        self._pool_size = connection_pool_size
        self._redis: Optional[Any] = None
        self._pubsub_tasks: Dict[str, asyncio.Task[None]] = {}
        self._closed = False

        logger.debug(
            "RedisBackend initialized",
            url=url.replace(":", ":*****@") if "@" in url else url,  # Mask password
            stream_ttl_seconds=stream_ttl_seconds,
            max_events_per_run=max_events_per_run,
        )

    async def _ensure_connection(self) -> Any:
        """Ensure Redis connection is established."""
        if self._redis is None:
            try:
                redis_client = aioredis.from_url(
                    self._url,
                    max_connections=self._pool_size,
                    decode_responses=True,
                )
                # Test connection
                await redis_client.ping()
                self._redis = redis_client
                logger.info("Redis connection established")
            except RedisConnectionError as e:
                logger.error("Failed to connect to Redis", error=str(e))
                raise BackendConnectionError(
                    f"Failed to connect to Redis: {e}",
                    backend="redis",
                ) from e
        return self._redis

    async def publish(self, channel: str, event: Dict[str, Any]) -> None:
        """
        Publish an event to a channel.

        Publishes to both Pub/Sub (real-time) and Streams (persistence).

        Args:
            channel: Channel name (e.g., "run:abc123")
            event: Event data dictionary
        """
        if self._closed:
            logger.warning("Publish called on closed backend", channel=channel)
            return

        try:
            redis = await self._ensure_connection()
            event_json = json.dumps(event, default=str)

            # Publish to Pub/Sub for real-time delivery
            pubsub_channel = _channel_key(channel)
            await redis.publish(pubsub_channel, event_json)

            logger.debug(
                "Event published to Redis",
                channel=channel,
                event_type=event.get("type"),
            )

        except RedisError as e:
            logger.error("Redis publish failed", channel=channel, error=str(e))
            raise BackendPublishError(
                f"Failed to publish event: {e}",
                backend="redis",
            ) from e

    async def subscribe(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to events on a channel via Pub/Sub.

        Args:
            channel: Channel name to subscribe to

        Yields:
            Event dictionaries as they are published
        """
        if self._closed:
            logger.warning("Subscribe called on closed backend", channel=channel)
            return

        try:
            redis = await self._ensure_connection()
            pubsub = redis.pubsub()
            pubsub_channel = _channel_key(channel)

            await pubsub.subscribe(pubsub_channel)
            logger.debug("Subscribed to Redis channel", channel=channel)

            try:
                while not self._closed:
                    try:
                        message = await asyncio.wait_for(
                            pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                            timeout=2.0,
                        )
                        if message is not None and message["type"] == "message":
                            try:
                                event = json.loads(message["data"])
                                yield event
                            except json.JSONDecodeError as e:
                                logger.warning(
                                    "Failed to decode event",
                                    channel=channel,
                                    error=str(e),
                                )
                    except asyncio.TimeoutError:
                        # Continue loop, check _closed flag
                        continue

            finally:
                await pubsub.unsubscribe(pubsub_channel)
                await pubsub.close()
                logger.debug("Unsubscribed from Redis channel", channel=channel)

        except RedisError as e:
            logger.error("Redis subscribe failed", channel=channel, error=str(e))
            raise BackendSubscribeError(
                f"Failed to subscribe: {e}",
                backend="redis",
            ) from e

    async def store_event(self, run_id: str, event: Dict[str, Any]) -> None:
        """
        Store an event in Redis Streams for later retrieval.

        Args:
            run_id: Run identifier
            event: Event data dictionary
        """
        if self._closed:
            return

        try:
            redis = await self._ensure_connection()
            stream_key = _stream_key(run_id)

            # Store event in stream
            # Use XADD with MAXLEN to limit stream size
            event_data = {
                "data": json.dumps(event, default=str),
                "sequence": str(event.get("sequence", 0)),
                "type": event.get("type", "unknown"),
            }

            await redis.xadd(
                stream_key,
                event_data,
                maxlen=self._max_events,
                approximate=True,
            )

            # Set TTL on the stream
            await redis.expire(stream_key, self._stream_ttl)

            logger.debug(
                "Event stored in Redis Stream",
                run_id=run_id,
                event_type=event.get("type"),
                sequence=event.get("sequence"),
            )

        except RedisError as e:
            logger.error("Redis store_event failed", run_id=run_id, error=str(e))
            # Don't raise - storage failure shouldn't break real-time delivery

    async def get_events(self, run_id: str, from_sequence: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve stored events from Redis Streams.

        Args:
            run_id: Run identifier
            from_sequence: Minimum sequence number to retrieve

        Returns:
            List of event dictionaries, ordered by sequence
        """
        try:
            redis = await self._ensure_connection()
            stream_key = _stream_key(run_id)

            # Read all events from stream
            messages = await redis.xrange(stream_key, "-", "+")

            events = []
            for _msg_id, data in messages:
                try:
                    event = json.loads(data.get("data", "{}"))
                    seq = event.get("sequence", 0)
                    if seq >= from_sequence:
                        events.append(event)
                except json.JSONDecodeError:
                    continue

            # Sort by sequence
            events.sort(key=lambda e: e.get("sequence", 0))

            logger.debug(
                "Events retrieved from Redis Stream",
                run_id=run_id,
                from_sequence=from_sequence,
                total_events=len(events),
            )

            return events

        except RedisError as e:
            logger.error("Redis get_events failed", run_id=run_id, error=str(e))
            return []

    async def close(self) -> None:
        """Close the Redis connection."""
        self._closed = True

        # Cancel any active pubsub tasks
        for task in self._pubsub_tasks.values():
            task.cancel()
        self._pubsub_tasks.clear()

        if self._redis is not None:
            await self._redis.close()
            self._redis = None

        logger.info("RedisBackend closed")

    async def clear_run(self, run_id: str) -> None:
        """
        Clear stored events for a run.

        Args:
            run_id: Run identifier to clear
        """
        try:
            redis = await self._ensure_connection()
            stream_key = _stream_key(run_id)
            await redis.delete(stream_key)
            logger.debug("Run events cleared from Redis", run_id=run_id)
        except RedisError as e:
            logger.warning("Failed to clear run events", run_id=run_id, error=str(e))

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is reachable, False otherwise
        """
        try:
            redis = await self._ensure_connection()
            await redis.ping()
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get backend statistics.

        Returns:
            Dict with connection and configuration info
        """
        return {
            "backend": "redis",
            "connected": self._redis is not None,
            "closed": self._closed,
            "stream_ttl_seconds": self._stream_ttl,
            "max_events_per_run": self._max_events,
            "pool_size": self._pool_size,
        }
