# Dockrion Runtime

FastAPI-based runtime server for deployed Dockrion agents.

## Overview

This package provides the runtime infrastructure for Dockrion agents:

- **App Factory**: `create_app()` builds a configured FastAPI application
- **Authentication**: API key validation middleware
- **Metrics**: Prometheus metrics for requests, latency, errors
- **Policy Engine**: Input validation, output redaction, safety checks
- **Endpoints**: Health, invoke, schema, metrics endpoints

## Usage

The runtime is typically used via generated code, but can be used directly:

```python
from dockrion_runtime import create_app
from dockrion_schema import DockSpec

# Load your spec
spec_data = {...}  # From Dockfile.yaml
spec = DockSpec.model_validate(spec_data)

# Create the app
app = create_app(
    spec=spec,
    agent_entrypoint="myagent.graph:build_graph"
)

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/invoke` | POST | Invoke the agent |
| `/invoke/stream` | POST | Streaming invocation (SSE) |
| `/schema` | GET | Input/output schema |
| `/info` | GET | Agent metadata |
| `/metrics` | GET | Prometheus metrics |

## Configuration

The runtime is configured via the `DockSpec` object which contains:

- Agent configuration (name, entrypoint, framework)
- Model configuration (provider, name, temperature)
- Auth configuration (mode, API keys)
- Policy configuration (redaction, tool allowlists)
- Expose configuration (host, port, CORS)

