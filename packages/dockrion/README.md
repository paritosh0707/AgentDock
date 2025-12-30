# Dockrion

[![PyPI version](https://badge.fury.io/py/dockrion.svg)](https://badge.fury.io/py/dockrion)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/paritosh0707/Dockrion)

**Deploy and manage AI agents with ease.**

Dockrion provides a complete toolkit for building, validating, and deploying AI agents powered by LangGraph, LangChain, and other frameworks. Define your agent in a simple YAML file and deploy it anywhere.

## 🚀 Installation

```bash
pip install dockrion
```

### Optional Features

```bash
# LangGraph framework support
pip install dockrion[langgraph]

# LangChain framework support
pip install dockrion[langchain]

# Runtime server (FastAPI + Uvicorn)
pip install dockrion[runtime]

# JWT authentication
pip install dockrion[jwt]

# Everything included
pip install dockrion[all]
```

## ⚡ Quick Start

### 1. Initialize a New Project

```bash
dockrion init my-agent
cd my-agent
```

This creates a `Dockfile.yaml` template:

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

### 2. Validate Your Configuration

```bash
dockrion validate
```

### 3. Test Locally

```bash
dockrion test --payload '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

### 4. Run the Server

```bash
dockrion run
```

Your agent is now accessible at `http://localhost:8080`.

### 5. Build & Deploy

```bash
# Build Docker image
dockrion build

# Deploy to your infrastructure
dockrion deploy
```

## 📦 What's Included

The `dockrion` package bundles everything you need:

| Module | Description |
|--------|-------------|
| `dockrion_cli` | Command-line interface for all operations |
| `dockrion_sdk` | SDK for building and testing agents |
| `dockrion_runtime` | FastAPI server for deployed agents |
| `dockrion_schema` | Dockfile YAML schema validation |
| `dockrion_adapters` | Framework adapters (LangGraph, LangChain) |
| `dockrion_policy` | Policy engine for redaction & tool gating |
| `dockrion_telemetry` | Prometheus metrics & structured logging |
| `dockrion_common` | Shared utilities and error handling |

## ✨ Features

- 🚀 **Simple Configuration** — Define your agent in a declarative YAML Dockfile
- 🔧 **Framework Agnostic** — Works with LangGraph, LangChain, and custom frameworks
- 🛡️ **Built-in Safety** — Policy engine for PII redaction and tool gating
- 📊 **Observability** — Prometheus metrics and structured JSON logging
- 🔐 **Security** — JWT authentication and API key support out of the box
- 🐳 **Container Ready** — Docker-first deployment with auto-generated Dockerfiles
- ⚡ **Fast Development** — Hot reload and local testing without containers
- 🧪 **Testing Tools** — Test your agent with payloads before deployment

## 🔧 CLI Commands

| Command | Description |
|---------|-------------|
| `dockrion init <name>` | Create a new agent project |
| `dockrion validate` | Validate Dockfile configuration |
| `dockrion test` | Test agent with sample payloads |
| `dockrion run` | Run agent server locally |
| `dockrion build` | Build Docker image |
| `dockrion deploy` | Deploy to target environment |
| `dockrion logs` | View agent logs |
| `dockrion doctor` | Diagnose setup issues |
| `dockrion version` | Show version information |

## 📚 Documentation

For full documentation, examples, and guides:

- 📖 [GitHub Repository](https://github.com/paritosh0707/Dockrion)
- 📋 [Installation Guide](https://github.com/paritosh0707/Dockrion/blob/main/docs/INSTALLATION_GUIDE.md)
- 🏗️ [Architecture](https://github.com/paritosh0707/Dockrion/blob/main/docs/DOCKER_RUNTIME_ARCHITECTURE.md)

## 🤝 Contributing

We welcome contributions! Please see our [GitHub repository](https://github.com/paritosh0707/Dockrion) for:

- Issue tracking
- Pull request guidelines
- Development setup instructions

## 👥 Authors

- **Paritosh Sharma** — [paritoshsharma0707@gmail.com](mailto:paritoshsharma0707@gmail.com)
- **Prakhar Agarwal** — [prakhara56@gmail.com](mailto:prakhara56@gmail.com)

## 📄 License

Apache-2.0 — See [LICENSE](https://github.com/paritosh0707/Dockrion/blob/main/LICENSE) for details.
