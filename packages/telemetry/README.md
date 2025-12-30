# dockrion-telemetry

Telemetry and observability helpers for Dockrion - metrics, logging, and monitoring utilities.

## Installation

```bash
pip install dockrion-telemetry
```

## Features

- **Prometheus Metrics**: Built-in Prometheus client integration for exposing metrics
- **Structured Logging**: Consistent logging utilities across Dockrion services
- **Observability Helpers**: Common patterns for monitoring AI agent deployments

## Usage

```python
from dockrion_telemetry.prometheus_utils import setup_metrics
from dockrion_telemetry.logger import get_logger

# Set up Prometheus metrics
setup_metrics()

# Get a configured logger
logger = get_logger(__name__)
logger.info("Agent started successfully")
```

## License

Apache-2.0

