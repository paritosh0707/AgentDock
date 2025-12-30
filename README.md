# Dockrion

[![PyPI version](https://badge.fury.io/py/dockrion.svg)](https://badge.fury.io/py/dockrion)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Deploy and manage AI agents with ease.**

Dockrion provides a complete toolkit for building, validating, and deploying AI agents powered by LangGraph, LangChain, and other frameworks.

## Installation

```bash
pip install dockrion
```

### With Optional Features

```bash
# LangGraph support
pip install dockrion[langgraph]

# LangChain support  
pip install dockrion[langchain]

# Runtime (for deploying agents as a server)
pip install dockrion[runtime]

# Everything
pip install dockrion[all]
```

## Quick Start

```bash
# Initialize a new agent project
dockrion init my-agent
cd my-agent

# Validate your Dockfile
dockrion validate

# Run your agent locally
dockrion run

# Deploy to production
dockrion deploy
```

## Features

- 🚀 **Easy Deployment** — Define your agent in a simple YAML Dockfile
- 🔧 **Framework Agnostic** — Works with LangGraph, LangChain, and more
- 🛡️ **Built-in Safety** — Policy engine for redaction and tool gating
- 📊 **Observability** — Prometheus metrics and structured logging
- 🔐 **Security** — JWT authentication and API key support
- 🐳 **Container Ready** — Docker-first deployment strategy

## Example Dockfile

```yaml
version: "1.0"

agent:
  name: my-agent
  entrypoint: app.graph:build_agent
  framework: langgraph

io_schema:
  input:
    type: object
    properties:
      messages:
        type: array
  output:
    type: object
    properties:
      response:
        type: string

expose:
  port: 8080
```

## Documentation

- [Installation Guide](docs/INSTALLATION_GUIDE.md)
- [Developer Journey](docs/DEVELOPER_JOURNEY.md)
- [Architecture](docs/DOCKER_RUNTIME_ARCHITECTURE.md)

## Development

```bash
# Clone the repository
git clone https://github.com/paritosh0707/Dockrion.git
cd Dockrion

# Setup development environment
uv venv && source .venv/bin/activate
make bootstrap-dev

# Run tests
make test

# Run CI checks
make ci
```

## Authors

- **Paritosh Sharma** — [paritoshsharma0707@gmail.com](mailto:paritoshsharma0707@gmail.com)
- **Prakhar Agarwal** — [prakhara56@gmail.com](mailto:prakhara56@gmail.com)

## License

Apache-2.0
