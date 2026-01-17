"""Tests for EventBus."""

import asyncio

import pytest


class TestEventBus:
    """Tests for EventBus."""

    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus, sample_run_id):
        """Should publish an event."""
        from dockrion_events import ProgressEvent

        event = ProgressEvent(
            run_id=sample_run_id,
            sequence=1,
            step="test",
            progress=0.5,
        )

        await event_bus.publish(sample_run_id, event)

        # Verify event was stored
        events = await event_bus.get_events(sample_run_id)
        assert len(events) == 1
        assert events[0].type == "progress"
        assert events[0].step == "test"

    @pytest.mark.asyncio
    async def test_subscribe_to_events(self, event_bus, sample_run_id):
        """Should subscribe and receive events."""
        from dockrion_events import CompleteEvent, ProgressEvent

        received_events = []

        async def subscriber():
            async for event in event_bus.subscribe(sample_run_id, include_stored=False):
                received_events.append(event)
                if event.type == "complete":
                    break

        # Start subscriber
        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Publish events
        progress = ProgressEvent(run_id=sample_run_id, sequence=1, step="test", progress=0.5)
        complete = CompleteEvent(run_id=sample_run_id, sequence=2, output={"result": "done"})

        await event_bus.publish(sample_run_id, progress)
        await event_bus.publish(sample_run_id, complete)

        # Wait for subscriber
        await asyncio.wait_for(task, timeout=2.0)

        assert len(received_events) == 2
        assert received_events[0].type == "progress"
        assert received_events[1].type == "complete"

    @pytest.mark.asyncio
    async def test_get_events_with_replay(self, event_bus, sample_run_id):
        """Should get stored events for replay."""
        from dockrion_events import ProgressEvent

        # Publish events
        for i in range(5):
            event = ProgressEvent(
                run_id=sample_run_id, sequence=i + 1, step=f"step_{i}", progress=i / 5
            )
            await event_bus.publish(sample_run_id, event)

        # Get events from sequence 3
        events = await event_bus.get_events(sample_run_id, from_sequence=3)

        assert len(events) == 3
        assert events[0].sequence == 3
        assert events[2].sequence == 5

    @pytest.mark.asyncio
    async def test_subscribe_with_stored_replay(self, event_bus, sample_run_id):
        """Should replay stored events when subscribing with from_sequence."""
        from dockrion_events import ProgressEvent

        # Pre-publish events
        for i in range(5):
            event = ProgressEvent(
                run_id=sample_run_id, sequence=i + 1, step=f"step_{i}", progress=i / 5
            )
            await event_bus.publish(sample_run_id, event)

        received_events = []

        async def subscriber():
            count = 0
            async for event in event_bus.subscribe(
                sample_run_id, from_sequence=3, include_stored=True
            ):
                received_events.append(event)
                count += 1
                if count >= 3:  # Just get the stored events
                    break

        task = asyncio.create_task(subscriber())
        await asyncio.wait_for(task, timeout=2.0)

        # Should have received events 3, 4, 5
        assert len(received_events) == 3
        assert received_events[0].sequence == 3

    @pytest.mark.asyncio
    async def test_close(self, event_bus):
        """Should close the event bus."""
        await event_bus.close()
        # Should not raise

    @pytest.mark.asyncio
    async def test_clear_run(self, event_bus, sample_run_id):
        """Should clear stored events for a run."""
        from dockrion_events import ProgressEvent

        # Publish events
        event = ProgressEvent(run_id=sample_run_id, sequence=1, step="test", progress=0.5)
        await event_bus.publish(sample_run_id, event)

        # Verify event exists
        events = await event_bus.get_events(sample_run_id)
        assert len(events) == 1

        # Clear run
        await event_bus.clear_run(sample_run_id)

        # Verify events cleared
        events = await event_bus.get_events(sample_run_id)
        assert len(events) == 0


class TestEventBusFactory:
    """Tests for EventBusFactory."""

    @pytest.mark.asyncio
    async def test_create_memory_backend(self):
        """Should create event bus with memory backend."""
        from dockrion_events.bus import EventBusFactory

        bus = await EventBusFactory.create("memory")
        assert bus is not None
        await bus.close()

    @pytest.mark.asyncio
    async def test_create_unknown_backend(self):
        """Should raise error for unknown backend."""
        from dockrion_events.bus import EventBusFactory

        with pytest.raises(ValueError, match="Unknown backend type"):
            await EventBusFactory.create("unknown")
