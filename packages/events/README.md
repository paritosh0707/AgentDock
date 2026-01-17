# Dockrion Events

Streaming and event infrastructure for Dockrion agent executions.

## Overview

The `dockrion-events` package provides real-time event delivery from agent executions to clients. It implements a three-layer architecture:

1. **Domain Events**: Event models representing what happened during execution
2. **Event Bus**: Abstraction layer for event routing and delivery
3. **Transport Backends**: Pluggable infrastructure (InMemory, Redis)

## Streaming Patterns

Dockrion supports two streaming patterns:

### Pattern A: Direct Streaming (`/invoke/stream`)
- Client makes request and receives events in the same connection
- Low-latency, suitable for real-time chat UIs
- Uses queue mode in StreamContext

### Pattern B: Async Runs (`/runs`)
- Client starts run, receives run ID, subscribes separately
- Supports reconnection and event replay
- Uses EventBus mode in StreamContext

## Features

- **Real-time Event Streaming**: Deliver events as they occur during agent execution
- **Dual Streaming Patterns**: Direct streaming (Pattern A) and async runs (Pattern B)
- **Event Filtering**: Configure which events to emit via Dockfile presets or allow-lists
- **Async Execution Model**: Fire-and-forget invocation with separate event subscription
- **Event Replay**: Reconnecting clients can receive missed events (Redis backend)
- **Multiple Subscribers**: Multiple clients can subscribe to the same run
- **Custom Events**: Users can emit domain-specific events from their agent code
- **Pluggable Backends**: Support for Redis (production) and in-memory (development)

## Installation

```bash
# Basic installation
pip install dockrion-events

# With Redis support
pip install dockrion-events[redis]
```

## Usage

### Event Models

```python
from dockrion_events import (
    StartedEvent,
    ProgressEvent,
    CheckpointEvent,
    TokenEvent,
    StepEvent,
    CompleteEvent,
    ErrorEvent,
)

# Events are automatically created by StreamContext
# but can also be created manually for testing
event = ProgressEvent(
    run_id="run-123",
    step="parsing",
    progress=0.5,
    message="Parsing document..."
)
```

### StreamContext (User API)

```python
from dockrion_events import StreamContext, get_current_context

# In handler mode - context is passed as parameter
def my_handler(payload: dict, context: StreamContext) -> dict:
    context.emit_progress("processing", 0.1, "Starting...")
    
    # Do work...
    context.checkpoint("intermediate", {"parsed": data})
    
    context.emit_progress("processing", 0.9, "Almost done...")
    return {"result": "done"}

# Alternative: access via thread-local
def my_node(state):
    context = get_current_context()
    if context:
        context.emit_step("my_node", duration_ms=150)
    return state
```

### Queue Mode (Pattern A)

For direct streaming, StreamContext can operate in queue mode where events
are stored internally and drained by the adapter:

```python
from dockrion_events import StreamContext, EventsFilter

# Create queue-mode context (no EventBus required)
filter = EventsFilter(["token", "step"])
context = StreamContext(
    run_id="run-123",
    queue_mode=True,
    events_filter=filter,
)

# Emit events (stored in internal queue)
context.sync_emit_token("Hello")
context.sync_emit_step("processing")

# Drain events for streaming
events = context.drain_queued_events()
for event in events:
    yield event.to_sse()
```

### Event Filtering

Filter which events are emitted using EventsFilter:

```python
from dockrion_events import EventsFilter

# Preset: optimized for chat UIs
filter = EventsFilter("chat")  # token, step, heartbeat

# Preset: all events for debugging
filter = EventsFilter("debug")

# Preset: only lifecycle events
filter = EventsFilter("minimal")  # started, complete, error, cancelled

# Explicit list
filter = EventsFilter(["token", "step", "custom:fraud_check"])

# Check if event is allowed
if filter.is_allowed("token"):
    context.emit_token("Hello")

# Get LangGraph stream modes
modes = filter.get_langgraph_stream_modes()  # ["messages", "updates"]
```

### EventBus

```python
from dockrion_events import EventBus, InMemoryBackend

# Create backend and bus
backend = InMemoryBackend()
bus = EventBus(backend)

# Publish events
await bus.publish(run_id, event)

# Subscribe to events
async for event in bus.subscribe(run_id):
    print(f"Received: {event.type}")
```

### Run Manager

```python
from dockrion_events import RunManager, RunStatus

manager = RunManager(event_bus)

# Create a run
run = await manager.create_run()
print(f"Created run: {run.run_id}")

# Update status
await manager.update_status(run.run_id, RunStatus.RUNNING)

# Set result on completion
await manager.set_result(run.run_id, {"output": "done"})
```

## Backends

### InMemory Backend

For development and testing. No external dependencies.

```python
from dockrion_events import InMemoryBackend

backend = InMemoryBackend()
```

### Redis Backend

For production. Supports multi-instance deployments and event replay.

```python
from dockrion_events import RedisBackend

backend = RedisBackend(
    url="redis://localhost:6379",
    stream_ttl_seconds=3600,
    max_events_per_run=1000,
)
```

## Event Types

### Mandatory Events (Always Emitted)

| Event | Description | Emitted By |
|-------|-------------|------------|
| `started` | Run begins execution | Runtime (automatic) |
| `complete` | Successful completion | Runtime (automatic) |
| `error` | Execution failure | Runtime (automatic) |
| `cancelled` | Run was cancelled | Runtime (on cancel) |

### Configurable Events

| Event | Description | Emitted By | Presets |
|-------|-------------|------------|---------|
| `token` | LLM token for streaming | LLM integration or user | chat, debug, all |
| `step` | Agent step/node completion | Framework or user | chat, debug, all |
| `progress` | Execution progress update | User code | debug, all |
| `checkpoint` | Intermediate state snapshot | User code | debug, all |
| `heartbeat` | Keep-alive signal | Runtime (automatic) | chat, debug, all |
| `custom` | User-defined event types | User code | debug, all |

### Presets

| Preset | Events Included | Use Case |
|--------|-----------------|----------|
| `minimal` | (mandatory only) | Background jobs, no UI |
| `chat` | token, step, heartbeat | Real-time chat UIs |
| `debug` | all events | Development, debugging |
| `all` | all events | Same as debug |

## Dockfile Configuration

Configure event filtering in your Dockfile:

```yaml
streaming:
  async_runs: true
  backend: memory
  events:
    allowed: chat  # Preset
    heartbeat_interval: 15
    max_run_duration: 3600
```

Or with explicit list:

```yaml
streaming:
  events:
    allowed:
      - token
      - step
      - custom:fraud_check
      - custom:analytics
```

## License

Apache-2.0
