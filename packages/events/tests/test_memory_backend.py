"""Tests for InMemoryBackend."""

import asyncio

import pytest


class TestInMemoryBackend:
    """Tests for InMemoryBackend."""

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self, memory_backend):
        """Should publish and receive events via subscription."""
        channel = "run:test-123"
        received_events = []

        async def subscriber():
            async for event in memory_backend.subscribe(channel):
                received_events.append(event)
                if event.get("type") == "complete":
                    break

        # Start subscriber task
        task = asyncio.create_task(subscriber())

        # Give subscriber time to connect
        await asyncio.sleep(0.1)

        # Publish events
        await memory_backend.publish(channel, {"type": "progress", "step": "test"})
        await memory_backend.publish(channel, {"type": "complete"})

        # Wait for subscriber to receive events
        await asyncio.wait_for(task, timeout=2.0)

        assert len(received_events) == 2
        assert received_events[0]["type"] == "progress"
        assert received_events[1]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_store_and_retrieve_events(self, memory_backend):
        """Should store and retrieve events."""
        run_id = "test-run-456"

        # Store events
        await memory_backend.store_event(run_id, {"type": "started", "sequence": 1})
        await memory_backend.store_event(run_id, {"type": "progress", "sequence": 2})
        await memory_backend.store_event(run_id, {"type": "complete", "sequence": 3})

        # Retrieve all events
        events = await memory_backend.get_events(run_id)
        assert len(events) == 3
        assert events[0]["sequence"] == 1
        assert events[2]["sequence"] == 3

    @pytest.mark.asyncio
    async def test_get_events_from_sequence(self, memory_backend):
        """Should retrieve events from a specific sequence."""
        run_id = "test-run-789"

        # Store events
        for i in range(1, 6):
            await memory_backend.store_event(run_id, {"type": "step", "sequence": i})

        # Retrieve from sequence 3
        events = await memory_backend.get_events(run_id, from_sequence=3)
        assert len(events) == 3
        assert events[0]["sequence"] == 3
        assert events[2]["sequence"] == 5

    @pytest.mark.asyncio
    async def test_max_events_limit(self):
        """Should limit stored events per run."""
        from dockrion_events import InMemoryBackend

        backend = InMemoryBackend(max_events_per_run=5)
        run_id = "test-run-limit"

        # Store more events than limit
        for i in range(10):
            await backend.store_event(run_id, {"type": "step", "sequence": i})

        # Should only have last 5 events
        events = await backend.get_events(run_id)
        assert len(events) == 5
        assert events[0]["sequence"] == 5
        assert events[4]["sequence"] == 9

    @pytest.mark.asyncio
    async def test_clear_run(self, memory_backend):
        """Should clear stored events for a run."""
        run_id = "test-run-clear"

        # Store events
        await memory_backend.store_event(run_id, {"type": "progress", "sequence": 1})
        await memory_backend.store_event(run_id, {"type": "complete", "sequence": 2})

        # Verify events exist
        events = await memory_backend.get_events(run_id)
        assert len(events) == 2

        # Clear run
        await memory_backend.clear_run(run_id)

        # Verify events are cleared
        events = await memory_backend.get_events(run_id)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_subscriber_count(self, memory_backend):
        """Should track subscriber count."""
        channel = "run:test-count"

        assert memory_backend.get_subscriber_count(channel) == 0

        async def subscriber():
            async for _ in memory_backend.subscribe(channel):
                break

        # Start subscriber
        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        assert memory_backend.get_subscriber_count(channel) == 1

        # Publish to end subscriber
        await memory_backend.publish(channel, {"type": "complete"})
        await asyncio.wait_for(task, timeout=2.0)

        # Wait for cleanup
        await asyncio.sleep(0.1)
        assert memory_backend.get_subscriber_count(channel) == 0

    @pytest.mark.asyncio
    async def test_close(self, memory_backend):
        """Should close and notify subscribers."""
        channel = "run:test-close"
        received_events = []

        async def subscriber():
            async for event in memory_backend.subscribe(channel):
                received_events.append(event)

        # Start subscriber
        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Close backend
        await memory_backend.close()

        # Subscriber should exit
        await asyncio.wait_for(task, timeout=2.0)

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, memory_backend):
        """Should deliver events to multiple subscribers."""
        channel = "run:test-multi"
        received1 = []
        received2 = []

        async def subscriber1():
            async for event in memory_backend.subscribe(channel):
                received1.append(event)
                if event.get("type") == "complete":
                    break

        async def subscriber2():
            async for event in memory_backend.subscribe(channel):
                received2.append(event)
                if event.get("type") == "complete":
                    break

        # Start subscribers
        task1 = asyncio.create_task(subscriber1())
        task2 = asyncio.create_task(subscriber2())
        await asyncio.sleep(0.1)

        # Publish events
        await memory_backend.publish(channel, {"type": "progress"})
        await memory_backend.publish(channel, {"type": "complete"})

        # Wait for subscribers
        await asyncio.wait_for(asyncio.gather(task1, task2), timeout=2.0)

        # Both should receive all events
        assert len(received1) == 2
        assert len(received2) == 2
