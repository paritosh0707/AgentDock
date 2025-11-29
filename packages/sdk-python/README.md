# Dockrion SDK

**Python SDK for deploying and managing AI agents**

The Dockrion SDK provides a simple, powerful interface for working with AI agents defined in Dockfiles. Use it to load, validate, deploy, and invoke agents locally or remotely.

## Features

- 🚀 **Load and Validate Dockfiles** - Parse YAML configurations with schema validation
- 🔧 **Environment Variable Expansion** - Support for `${VAR}` and `${VAR:-default}` syntax
- 🎯 **Local Agent Invocation** - Test agents without deploying servers
- 🐳 **Docker Deployment** - Build and deploy agents as Docker containers
- 🏃 **Local Server Mode** - Run agents as FastAPI servers for development
- 📊 **Comprehensive Validation** - Detailed error messages and warnings
- 🔌 **Framework Agnostic** - Works with LangGraph, LangChain, and more

## Installation

```bash
# Install SDK
cd packages/sdk-python
uv sync

# Install with dev dependencies (for testing)
uv sync --extra dev
```

## Quick Start

### 1. Load and Validate a Dockfile

```python
from dockrion_sdk import load_dockspec, validate_dockspec

# Load a Dockfile
spec = load_dockspec("Dockfile.yaml")
print(f"Agent: {spec.agent.name}")
print(f"Framework: {spec.agent.framework}")

# Validate with detailed results
result = validate_dockspec("Dockfile.yaml")
if result["valid"]:
    print(f"✅ {result['message']}")
else:
    print(f"❌ Errors: {result['errors']}")
```

### 2. Invoke an Agent Locally

```python
from dockrion_sdk import invoke_local

# Invoke agent directly (no server needed)
result = invoke_local("Dockfile.yaml", {
    "document_text": "INVOICE #12345...",
    "currency_hint": "USD"
})

print(f"Result: {result}")
```

### 3. Run Agent as Local Server

```python
from dockrion_sdk import run_local

# Start agent server (development mode)
proc = run_local("Dockfile.yaml")

# Server is now running at http://localhost:8080
# Test with: curl -X POST http://localhost:8080/invoke -d '{"text":"hello"}'

# Stop the server when done
proc.terminate()
```

### 4. Deploy Agent to Docker

```python
from dockrion_sdk import deploy

# Build Docker image
result = deploy("Dockfile.yaml", target="local")
print(f"Built image: {result['image']}")

# Run the container:
# docker run -p 8080:8080 Dockrion/your-agent:dev
```

## API Reference

### Core Functions

#### `load_dockspec(path: str) -> DockSpec`

Load and validate a Dockfile from the filesystem.

**Parameters:**
- `path`: Path to the Dockfile (typically "Dockfile.yaml")

**Returns:**
- `DockSpec`: Validated Dockfile specification

**Raises:**
- `ValidationError`: If file not found, invalid YAML, or schema validation fails

**Example:**
```python
spec = load_dockspec("Dockfile.yaml")
print(spec.agent.name)  # "invoice-copilot"
```

---

#### `invoke_local(dockfile_path: str, payload: dict) -> dict`

Invoke an agent locally without starting a server.

**Parameters:**
- `dockfile_path`: Path to the Dockfile
- `payload`: Input data to pass to the agent

**Returns:**
- `dict`: Agent response

**Raises:**
- `ValidationError`: If Dockfile is invalid
- `DockrionError`: If agent loading or invocation fails

**Example:**
```python
result = invoke_local("Dockfile.yaml", {
    "text": "Analyze this document..."
})
print(result["output"])
```

---

#### `validate_dockspec(path: str) -> dict`

Validate a Dockfile and return detailed results.

**Parameters:**
- `path`: Path to the Dockfile to validate

**Returns:**
- Dictionary with keys:
  - `valid` (bool): Whether the Dockfile is valid
  - `errors` (List[str]): List of error messages
  - `warnings` (List[str]): List of warnings
  - `spec` (DockSpec): Validated spec (if valid)
  - `message` (str): Summary message

**Example:**
```python
result = validate_dockspec("Dockfile.yaml")
if result["valid"]:
    print(f"✅ {result['message']}")
    if result["warnings"]:
        print(f"⚠️  Warnings: {result['warnings']}")
else:
    print(f"❌ Errors:")
    for error in result["errors"]:
        print(f"  - {error}")
```

---

#### `deploy(dockfile_path: str, target: str = "local") -> dict`

Deploy an agent to a target environment.

**Parameters:**
- `dockfile_path`: Path to the Dockfile
- `target`: Deployment target ("local" for V1, "remote" in V1.1+)

**Returns:**
- Dictionary with deployment information:
  - `image` (str): Docker image name
  - `status` (str): "built" or "failed"
  - `agent_name` (str): Name of the agent

**Raises:**
- `DockrionError`: If deployment fails

**Example:**
```python
result = deploy("Dockfile.yaml")
print(f"Image: {result['image']}")
# Run: docker run -p 8080:8080 {result['image']}
```

---

#### `run_local(dockfile_path: str) -> subprocess.Popen`

Run an agent locally without Docker (development mode).

**Parameters:**
- `dockfile_path`: Path to the Dockfile

**Returns:**
- `subprocess.Popen`: Running server process

**Raises:**
- `DockrionError`: If startup fails

**Example:**
```python
proc = run_local("Dockfile.yaml")
# Server running at http://localhost:8080
# ...do testing...
proc.terminate()  # Stop server
```

---

### Utility Functions

#### `expand_env_vars(data: Any) -> Any`

Recursively expand environment variables in data structures.

Supports:
- `${VAR}` - Required variable
- `${VAR:-default}` - Variable with default value

**Example:**
```python
import os
os.environ["MODEL"] = "gpt-4"

data = {"model": "${MODEL}", "fallback": "${MISSING:-gpt-3.5}"}
result = expand_env_vars(data)
# {"model": "gpt-4", "fallback": "gpt-3.5"}
```

---

### Log Functions

#### `get_local_logs(agent_name: str, lines: int = 100) -> List[str]`

Get logs from a locally running agent.

**Example:**
```python
logs = get_local_logs("invoice-copilot", lines=50)
for line in logs:
    print(line)
```

---

## Environment Variables

The SDK supports environment variable expansion in Dockfiles:

```yaml
version: "1.0"
agent:
  name: my-agent
  entrypoint: app.graph:build_graph
  framework: langgraph
model:
  provider: openai
  name: ${MODEL_NAME:-gpt-4o-mini}  # Default value
  api_key: ${OPENAI_API_KEY}         # Required
```

Set variables before loading:
```bash
export OPENAI_API_KEY="sk-..."
export MODEL_NAME="gpt-4"
```

Or in Python:
```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
spec = load_dockspec("Dockfile.yaml")
```

---

## Common Use Cases

### Development Workflow

```python
from dockrion_sdk import validate_dockspec, run_local

# 1. Validate Dockfile
result = validate_dockspec("Dockfile.yaml")
if not result["valid"]:
    print("Fix errors:", result["errors"])
    exit(1)

# 2. Run locally for testing
proc = run_local("Dockfile.yaml")

# 3. Test the agent
import requests
response = requests.post(
    "http://localhost:8080/invoke",
    json={"text": "test input"}
)
print(response.json())

# 4. Stop server
proc.terminate()
```

### Production Deployment

```python
from dockrion_sdk import deploy

# Build Docker image
result = deploy("Dockfile.yaml", target="local")
print(f"Built: {result['image']}")

# Deploy to production (V1.1+)
# result = deploy("Dockfile.yaml", target="production")
```

### Testing Agent Logic

```python
from dockrion_sdk import invoke_local

# Test cases
test_cases = [
    {"input": "test1", "expected": "output1"},
    {"input": "test2", "expected": "output2"},
]

for case in test_cases:
    result = invoke_local("Dockfile.yaml", {"text": case["input"]})
    assert result["output"] == case["expected"]
```

---

## Error Handling

The SDK uses typed exceptions from `dockrion-common`:

```python
from dockrion_sdk import load_dockspec, invoke_local
from dockrion_common.errors import ValidationError, DockrionError

try:
    spec = load_dockspec("Dockfile.yaml")
    result = invoke_local("Dockfile.yaml", payload)
except ValidationError as e:
    # Dockfile validation failed
    print(f"Validation error: {e}")
except DockrionError as e:
    # Agent execution failed
    print(f"Agent error: {e}")
except Exception as e:
    # Unexpected error
    print(f"Unexpected error: {e}")
```

---

## Testing

Run the test suite:

```bash
cd packages/sdk-python

# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_client.py -v

# Run with coverage
uv run pytest tests/ --cov=dockrion_sdk --cov-report=term-missing
```

---

## Architecture

The SDK follows a clean architecture:

```
┌─────────────────────────────────────────┐
│         Dockrion SDK (This Package)    │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ client.py│  │validate.py│  │deploy.py│
│  │          │  │          │  │        ││
│  │ load     │  │ validate │  │ deploy ││
│  │ invoke   │  │          │  │ run    ││
│  └──────────┘  └──────────┘  └────────┘│
└─────────────────────────────────────────┘
            │          │          │
            ▼          ▼          ▼
┌─────────────────────────────────────────┐
│       Foundation Packages                │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │  schema  │  │  common  │  │adapters││
│  │          │  │          │  │        ││
│  │ DockSpec │  │  Errors  │  │LangGraph│
│  │ Validate │  │  Utils   │  │Adapter ││
│  └──────────┘  └──────────┘  └────────┘│
└─────────────────────────────────────────┘
```

**Dependencies:**
- `dockrion-schema`: Dockfile schema and validation
- `dockrion-common`: Shared utilities and errors
- `dockrion-adapters`: Framework adapters for agent execution

---

## Troubleshooting

### "Dockfile not found"
**Problem:** File path is incorrect or file doesn't exist.  
**Solution:** Check the file path and ensure the file exists.

```python
from pathlib import Path
if not Path("Dockfile.yaml").exists():
    print("File not found!")
```

### "Invalid YAML"
**Problem:** YAML syntax error in Dockfile.  
**Solution:** Validate YAML syntax using a linter or online validator.

### "Environment variable not set"
**Problem:** Required environment variable is missing.  
**Solution:** Set the variable or use default syntax:

```yaml
model:
  api_key: ${API_KEY:-default_value}  # Provides default
```

### "Docker not available"
**Problem:** Docker is not installed or not running.  
**Solution:** Install Docker and ensure the daemon is running.

```bash
docker --version  # Check if Docker is available
```

### "Agent loading failed"
**Problem:** Agent entrypoint is incorrect or module not found.  
**Solution:** Verify the entrypoint format and ensure the module is in PYTHONPATH:

```python
# Correct format: "module.path:function_name"
agent:
  entrypoint: examples.invoice_copilot.app.graph:build_graph
```

---

## Integration with Other Packages

### With Adapters Package

```python
from dockrion_sdk import load_dockspec
from dockrion_adapters import get_adapter

# Load Dockfile
spec = load_dockspec("Dockfile.yaml")

# Get adapter and use directly
adapter = get_adapter(spec.agent.framework)
adapter.load(spec.agent.entrypoint)
result = adapter.invoke({"input": "data"})
```

### With CLI Package

The CLI package uses SDK functions internally:

```bash
# CLI uses sdk.validate_dockspec()
Dockrion validate Dockfile.yaml

# CLI uses sdk.deploy()
Dockrion deploy Dockfile.yaml
```

---

## Roadmap

### V1.0 (Current)
- ✅ Local Dockfile loading and validation
- ✅ Local agent invocation
- ✅ Docker deployment
- ✅ Development server mode

### V1.1 (Planned)
- 🔄 Remote deployment via Controller
- 🔄 Agent versioning and rollbacks
- 🔄 Real-time log streaming
- 🔄 Enhanced policy enforcement

### V2.0 (Future)
- 🔮 Multi-agent orchestration
- 🔮 A/B testing support
- 🔮 Auto-scaling configuration
- 🔮 Cost tracking and optimization

---

## Contributing

Contributions are welcome! Please:

1. Write tests for new features
2. Follow the existing code style
3. Update documentation
4. Ensure all tests pass

---

## License

Part of the Dockrion project. See root LICENSE file.

---

## Support

- **Documentation**: See `/docs` in the repository
- **Examples**: Check `/examples` directory
- **Issues**: Open a GitHub issue with `[sdk]` tag

---

## Version

**Current Version**: 0.1.0  
**Status**: MVP Complete  
**Python**: 3.12+

