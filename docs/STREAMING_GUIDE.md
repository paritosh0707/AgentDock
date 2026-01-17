# Dockrion Streaming Guide

Comprehensive guide to streaming events from Dockrion agents.

## Architecture Overview

Dockrion supports two streaming patterns to accommodate different use cases:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Agent Code                              │
│                   context.sync_emit_token("Hello")                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         StreamContext                                │
│              • Automatic sequence numbering                          │
│              • Event filtering (via EventsFilter)                    │
│              • Queue mode (Pattern A) or Bus mode (Pattern B)        │
└─────────────────────────────────────────────────────────────────────┘
                          │                    │
            ┌─────────────┘                    └─────────────┐
            ▼                                                ▼
┌─────────────────────────┐                    ┌─────────────────────────┐
│    Pattern A: Queue     │                    │   Pattern B: EventBus   │
│   /invoke/stream        │                    │      /runs endpoint     │
│   (direct streaming)    │                    │   (async execution)     │
└─────────────────────────┘                    └─────────────────────────┘
            │                                                │
            ▼                                                ▼
┌─────────────────────────┐                    ┌─────────────────────────┐
│  drain_queued_events()  │                    │    EventBus.publish()   │
│  → SSE Response         │                    │    → Subscribers        │
└─────────────────────────┘                    └─────────────────────────┘
```

## Pattern A: Direct Streaming (`/invoke/stream`)

Best for real-time chat UIs where low latency is critical.

### How It Works

1. Client makes POST request to `/invoke/stream`
2. Server processes request and streams SSE events in the same connection
3. Events are yielded as they occur (no intermediate storage)

### Example Request

```bash
curl -X POST http://localhost:8080/invoke/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!"}'
```

### Example Response (SSE)

```
event: started
data: {"request_id": "abc-123", "type": "started"}

event: step
data: {"request_id": "abc-123", "type": "step", "node": "process"}

event: token
data: {"request_id": "abc-123", "content": "Hello"}

event: complete
data: {"request_id": "abc-123", "type": "complete", "latency_seconds": 1.5}
```

> **Note**: Pattern A uses `request_id` (not `run_id`) because this is a correlation ID
> for client-side use only. There is no server-side persistence or resumability.
> For managed runs, use Pattern B which provides true `run_id` with full lifecycle management.

### When to Use

- Real-time chat applications
- Interactive UIs requiring immediate feedback
- Simple request-response with streaming output
- Single client per invocation

### Key Characteristics

| Feature | Pattern A |
|---------|-----------|
| Identifier | `request_id` (correlation only) |
| Persistence | None |
| Resumability | No - if connection drops, data is lost |
| Multiple subscribers | No |
| Latency | Lowest (direct streaming) |

## Pattern B: Async Runs (`/runs`)

Best for long-running tasks and production deployments.

### How It Works

1. Client POSTs to `/runs` to start execution
2. Server returns run ID immediately
3. Client subscribes to `/runs/{run_id}/events` via SSE
4. Events are delivered through EventBus

### Example Flow

```bash
# 1. Start run
curl -X POST http://localhost:8080/runs \
  -H "Content-Type: application/json" \
  -d '{"text": "Process this document..."}'

# Response: {"run_id": "run-456", "status": "accepted", "events_url": "/runs/run-456/events"}

# 2. Subscribe to events
curl http://localhost:8080/runs/run-456/events

# 3. Check status
curl http://localhost:8080/runs/run-456

# 4. Cancel if needed
curl -X DELETE http://localhost:8080/runs/run-456
```

### When to Use

- Long-running tasks (document processing, analysis)
- Production environments (Redis backend for scaling)
- Multiple subscribers to same run
- Reconnection with event replay needed

### Key Characteristics

| Feature | Pattern B |
|---------|-----------|
| Identifier | `run_id` (server-managed) |
| Persistence | Yes (in-memory or Redis) |
| Resumability | Yes - reconnect with `from_sequence` |
| Multiple subscribers | Yes |
| Latency | Slightly higher (EventBus overhead) |

## Pattern Comparison

| Aspect | Pattern A (`/invoke/stream`) | Pattern B (`/runs`) |
|--------|------------------------------|---------------------|
| **ID Type** | `request_id` | `run_id` |
| **Purpose** | Correlation only | Full lifecycle management |
| **Storage** | None | EventBus backend |
| **Reconnect** | Not supported | Supported |
| **Cancel** | Close connection | DELETE /runs/{id} |
| **Best For** | Real-time chat | Production workloads |

## Event Filtering

Control which events are emitted to reduce bandwidth and improve performance.

### Presets

| Preset | Events | Use Case |
|--------|--------|----------|
| `minimal` | (mandatory only) | Background jobs |
| `chat` | token, step, heartbeat | Chat UIs |
| `debug` | all events | Development |
| `all` | all events | Full visibility |

### Mandatory Events

These events are ALWAYS emitted regardless of filter configuration:
- `started` - Run began
- `complete` - Run finished successfully
- `error` - Run failed
- `cancelled` - Run was cancelled

### Configurable Events

These can be enabled/disabled via configuration:
- `token` - LLM token streaming
- `step` - Step/node completion
- `progress` - Progress percentage
- `checkpoint` - Intermediate state
- `heartbeat` - Keep-alive signal
- `custom` - User-defined events

## Dockfile Configuration

### Basic Configuration

```yaml
# Enable streaming in expose
expose:
  rest: true
  streaming: sse
  port: 8080

# Configure streaming behavior
streaming:
  async_runs: true        # Enable /runs endpoint (Pattern B)
  backend: memory         # Backend: memory or redis
  events:
    allowed: chat         # Preset or list
    heartbeat_interval: 15
    max_run_duration: 3600
```

### Event Presets

```yaml
streaming:
  events:
    allowed: chat  # token, step, heartbeat
```

### Explicit Event List

```yaml
streaming:
  events:
    allowed:
      - token
      - step
      - custom:fraud_check    # Specific custom event
      - custom:analytics
```

### All Custom Events

```yaml
streaming:
  events:
    allowed:
      - token
      - step
      - custom  # Wildcard: all custom events allowed
```

### Redis Backend (Production)

```yaml
streaming:
  async_runs: true
  backend: redis
  redis:
    url: redis://localhost:6379
    stream_ttl_seconds: 3600
    max_events_per_run: 1000
    connection_pool_size: 10
```

## Emitting Events from Agent Code

### Using StreamContext

```python
from dockrion_events import get_current_context

def my_node(state):
    context = get_current_context()
    if context:
        # Emit progress
        context.sync_emit_progress("processing", 0.5, "Halfway done")
        
        # Emit checkpoint with data
        context.sync_checkpoint("intermediate", {"parsed": True})
        
        # Emit custom event
        context.sync_emit("fraud_check", {"passed": True, "score": 0.02})
        
        # Emit step completion
        context.sync_emit_step("my_node", duration_ms=150)
    
    return state
```

### Custom Events

```python
# Emit any custom event type
context.sync_emit("analytics", {
    "user_id": "123",
    "action": "query_submitted",
    "metadata": {"query_length": 50}
})

# In Dockfile, allow specific custom events:
# allowed:
#   - custom:analytics
#   - custom:fraud_check
```

## CLI Commands

### Initialize with Streaming

```bash
# Basic streaming
dockrion init my-agent --streaming sse

# With events preset
dockrion init my-agent --streaming-events chat

# Enable async runs
dockrion init my-agent --async-runs --streaming-events chat

# Custom event list
dockrion init my-agent --streaming-events "token,step,custom:fraud"

# Production setup with Redis
dockrion init my-agent --async-runs --streaming-backend redis
```

### Add Streaming to Existing Dockfile

```bash
# Add streaming section
dockrion add streaming --events chat --async-runs

# Add with Redis
dockrion add streaming --events debug --backend redis
```

## Performance Considerations

### Pattern A (Direct Streaming)

- **Pros**: Lowest latency, simple architecture
- **Cons**: No reconnection, single subscriber per request
- **Memory**: Events not stored, minimal overhead

### Pattern B (Async Runs)

- **Pros**: Reconnection, event replay, multiple subscribers
- **Cons**: Slightly higher latency, requires backend
- **Memory**: Events stored until TTL expires

### Event Filtering Benefits

1. **Bandwidth**: Fewer events = less data transfer
2. **Performance**: Filter at source, not client
3. **Cost**: LLM token events can be high volume

### Recommended Presets by Use Case

| Use Case | Recommended Preset |
|----------|-------------------|
| Chat UI (production) | `chat` |
| Chat UI (development) | `debug` |
| Background processing | `minimal` |
| Analytics/monitoring | `debug` or custom list |
| API integration | `minimal` + custom events |

## Troubleshooting

### Events Not Appearing

1. Check filter configuration in Dockfile
2. Verify event type is allowed
3. Check if custom event uses correct pattern (`custom:name`)

### High Latency

1. Consider Pattern A for lower latency
2. Reduce event volume with filtering
3. Use `chat` preset for chat UIs

### Connection Drops

1. Enable heartbeat events
2. Use Pattern B with Redis for production
3. Implement client-side reconnection

### Memory Issues

1. Set appropriate `max_run_duration`
2. Use Redis backend for high-volume
3. Filter unnecessary events

## API Reference

### Event Types

| Type | Fields |
|------|--------|
| `started` | `run_id`, `agent_name`, `framework` |
| `progress` | `run_id`, `step`, `progress`, `message` |
| `checkpoint` | `run_id`, `name`, `data` |
| `token` | `run_id`, `content`, `finish_reason` |
| `step` | `run_id`, `node_name`, `duration_ms`, `input_keys`, `output_keys` |
| `complete` | `run_id`, `output`, `latency_seconds`, `metadata` |
| `error` | `run_id`, `error`, `code`, `details` |
| `heartbeat` | `run_id` |
| `cancelled` | `run_id`, `reason` |

### SSE Format

```
event: <event_type>
data: <json_payload>

```

Each event ends with two newlines. The `event` field specifies the type,
and `data` contains the JSON payload.
