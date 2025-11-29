# Dockrion CLI

**Command-line interface for deploying and managing AI agents**

The Dockrion CLI provides a simple, powerful interface for working with AI agents. Use it to validate Dockfiles, test agents locally, build Docker images, and deploy to production.

## Features

- 🎨 **Rich Terminal Output** - Beautiful, colorful displays with progress indicators
- ✅ **Comprehensive Validation** - Catch errors before deployment
- 🧪 **Local Testing** - Test agents without starting servers
- 🐳 **Docker Integration** - Build and deploy containerized agents
- 🔧 **Development Server** - Run agents locally with hot reload
- 📊 **Health Diagnostics** - Check your setup with `doctor` command
- 🚀 **Quick Start** - Initialize new projects with templates

## Installation

```bash
# Install from source
cd packages/cli
uv sync

# Install with dev dependencies
uv sync --extra dev
```

## Quick Start

```bash
# 1. Create a new agent project
Dockrion init my-agent

# 2. Edit the generated Dockfile.yaml
# (implement your agent logic)

# 3. Validate your configuration
Dockrion validate

# 4. Test your agent locally
Dockrion test --payload '{"text": "hello"}'

# 5. Run development server
Dockrion run

# 6. Build for production
Dockrion build
```

## Commands

### `Dockrion validate [PATH]`

Validate a Dockfile configuration.

**Options:**
- `--verbose`, `-v` - Show detailed output including full spec
- `--quiet`, `-q` - Only show errors, suppress warnings

**Examples:**
```bash
Dockrion validate
Dockrion validate custom/Dockfile.yaml
Dockrion validate --verbose
```

---

### `Dockrion test [PATH]`

Test an agent locally without starting a server.

**Options:**
- `--payload`, `-p` TEXT - JSON payload as string
- `--payload-file`, `-f` PATH - Path to JSON file with payload
- `--output`, `-o` PATH - Save output to file
- `--verbose`, `-v` - Show detailed output

**Examples:**
```bash
# Test with inline JSON
Dockrion test --payload '{"text": "analyze this"}'

# Test with payload file
Dockrion test --payload-file input.json

# Save output to file
Dockrion test -f input.json -o output.json
```

---

### `Dockrion build [PATH]`

Build a Docker image for the agent.

**Options:**
- `--target` TEXT - Deployment target (default: local)
- `--verbose`, `-v` - Show detailed output

**Examples:**
```bash
Dockrion build
Dockrion build custom/Dockfile.yaml
Dockrion build --verbose
```

---

### `Dockrion run [PATH]`

Run agent server locally for development.

**Options:**
- `--verbose`, `-v` - Show detailed output

**Examples:**
```bash
Dockrion run
Dockrion run custom/Dockfile.yaml
```

**Endpoints exposed:**
- `POST /invoke` - Invoke the agent
- `GET /health` - Health check
- `GET /schema` - Input/output schema
- `GET /metrics` - Prometheus metrics

Press `Ctrl+C` to stop the server.

---

### `Dockrion logs AGENT`

View logs from a running agent.

**Options:**
- `--lines`, `-n` INTEGER - Number of lines to show (default: 100)
- `--follow`, `-f` - Follow log output in real-time
- `--verbose`, `-v` - Show detailed output

**Examples:**
```bash
Dockrion logs invoice-copilot
Dockrion logs invoice-copilot --lines 50
Dockrion logs invoice-copilot --follow
```

---

### `Dockrion init NAME`

Create a new Dockfile template.

**Options:**
- `--output`, `-o` PATH - Output file path (default: Dockfile.yaml)
- `--force`, `-f` - Overwrite existing file without asking

**Examples:**
```bash
Dockrion init my-agent
Dockrion init my-agent --output custom/Dockfile.yaml
Dockrion init my-agent --force
```

---

### `Dockrion version`

Show Dockrion version information.

**Example:**
```bash
Dockrion version
```

---

### `Dockrion doctor`

Diagnose common issues with your setup.

Checks for:
- Python version (3.12+)
- Docker installation
- Dockfile presence and validity
- Dockrion package installations

**Example:**
```bash
Dockrion doctor
```

---

## Complete Workflow Example

```bash
# Step 1: Initialize a new agent
Dockrion init invoice-copilot

# Step 2: Edit Dockfile.yaml
# Set entrypoint, configure model, define schema

# Step 3: Implement your agent
# Create app/main.py with build_agent() function

# Step 4: Validate configuration
Dockrion validate
# ✅ Dockfile is valid. Agent: invoice-copilot, Framework: langgraph

# Step 5: Test locally
Dockrion test --payload '{"document_text": "INVOICE #123..."}'
# ✅ Agent invocation successful
# Output: { "vendor": "...", "total": 1299.0, ... }

# Step 6: Run development server
Dockrion run
# ✅ Server started at http://0.0.0.0:8080
# Available endpoints:
#   • POST http://0.0.0.0:8080/invoke
#   • GET  http://0.0.0.0:8080/health

# Step 7: Test via HTTP
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"document_text": "INVOICE #123..."}'

# Step 8: Build Docker image
Dockrion build
# ✅ Successfully built image: Dockrion/invoice-copilot:dev

# Step 9: Deploy to production
docker run -p 8080:8080 Dockrion/invoice-copilot:dev
```

---

## Error Handling

The CLI provides helpful error messages with actionable tips:

```bash
$ Dockrion validate broken.yaml
❌ Validation failed

Validation Errors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Invalid entrypoint format: missing ':'
• Field 'io_schema' is required

💡 Tip: Check the documentation for Dockfile schema requirements
```

---

## Output Formats

The CLI uses rich terminal output with colors and formatting:

- ✅ **Green** - Success messages
- ❌ **Red** - Error messages  
- ⚠️ **Yellow** - Warnings
- ℹ️ **Blue** - Informational messages
- **Cyan** - Commands and code
- **Dim** - Tips and hints

---

## Environment Integration

### CI/CD Pipelines

Use `--quiet` flag for CI/CD:

```bash
# GitLab CI
script:
  - Dockrion validate --quiet
  - Dockrion test --payload-file test.json
  - Dockrion build

# GitHub Actions
- name: Validate Dockfile
  run: Dockrion validate --quiet
```

### Docker Compose

```yaml
version: '3.8'
services:
  agent:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    command: Dockrion run
```

---

## Troubleshooting

### "Docker not found"

**Solution:** Install Docker:
```bash
# Check installation
docker --version

# Run diagnostics
Dockrion doctor
```

### "File not found: Dockfile.yaml"

**Solution:** Create a Dockfile:
```bash
Dockrion init my-agent
```

### "Invalid YAML in Dockfile"

**Solution:** Check YAML syntax:
```bash
# Use online validator or
python -c "import yaml; yaml.safe_load(open('Dockfile.yaml'))"
```

### "Agent loading failed"

**Solution:** Verify entrypoint:
```bash
# Ensure module is importable
python -c "from app.main import build_agent; print(build_agent())"
```

---

## Integration with SDK

The CLI wraps SDK functions with rich output:

```python
# SDK usage (programmatic)
from dockrion_sdk import invoke_local
result = invoke_local("Dockfile.yaml", payload)

# CLI usage (terminal)
$ Dockrion test --payload '{"text": "test"}'
```

Both do the same thing, CLI adds:
- Beautiful terminal output
- Progress indicators
- Error formatting
- Interactive prompts

---

## Development

### Running Tests

```bash
cd packages/cli

# Run all tests
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/test_validate_cmd.py -v

# Run with coverage
uv run pytest tests/ --cov=dockrion_cli --cov-report=term-missing
```

### Adding New Commands

1. Create command file in `dockrion_cli/`:
```python
# my_cmd.py
import typer
from .utils import console, success

app = typer.Typer()

@app.command(name="mycommand")
def mycommand():
    """My new command."""
    success("It works!")
```

2. Register in `main.py`:
```python
from . import my_cmd

app.command()(my_cmd.mycommand)
```

3. Add tests in `tests/test_my_cmd.py`

4. Update README

---

## Architecture

```
Dockrion (CLI)
├── validate    → sdk.validate_dockspec()
├── test        → sdk.invoke_local()
├── build       → sdk.deploy()
├── run         → sdk.run_local()
├── logs        → sdk.get_local_logs()
├── init        → template generation
├── version     → package introspection
└── doctor      → diagnostics
```

**Dependencies:**
- `typer` - CLI framework
- `rich` - Terminal formatting
- `dockrion-sdk` - Core functionality

---

## Roadmap

### V1.0 (Current)
- ✅ All core commands
- ✅ Rich output formatting
- ✅ Comprehensive error handling
- ✅ Local development workflow

### V1.1 (Planned)
- 🔄 Remote deployment via Controller
- 🔄 Agent versioning and rollbacks
- 🔄 Real-time log streaming
- 🔄 Interactive configuration wizard

### V2.0 (Future)
- 🔮 Plugin system
- 🔮 Custom templates
- 🔮 Multi-agent orchestration
- 🔮 Performance profiling

---

## Contributing

Contributions welcome! Please:

1. Write tests for new commands
2. Follow existing code style
3. Update documentation
4. Ensure all tests pass

---

## Support

- **Documentation**: See `/docs` in repository
- **Examples**: Check `/examples` directory
- **Issues**: Open GitHub issue with `[cli]` tag

---

## License

Part of the Dockrion project. See root LICENSE file.

---

## Version

**Current Version**: 0.1.0  
**Status**: MVP Complete  
**Python**: 3.12+  
**Tested Platforms**: Windows, Linux, macOS

