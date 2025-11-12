# AgentDock Package Installation Guide

Complete guide for installing all AgentDock packages in your development environment.

---

## Prerequisites

- Python 3.12+
- `uv` package manager (recommended) or `pip`
- Git repository cloned

---

## Quick Start

### Option 1: Using uv (Recommended)

```bash
# From repository root
cd /Users/prakharagarwal/AgentDock

# Install all packages in development mode
uv pip install -e packages/common-py -e packages/schema

# Or with dev dependencies
uv pip install -e "packages/common-py[dev]" -e "packages/schema[dev]"
```

### Option 2: Using pip

```bash
# From repository root
cd /Users/prakharagarwal/AgentDock

# Activate virtual environment first
source .venv/bin/activate

# Install all packages in development mode
pip install -e packages/common-py -e packages/schema

# Or with dev dependencies
pip install -e "packages/common-py[dev]" -e "packages/schema[dev]"
```

---

## Detailed Installation Options

### Method 1: Development Mode (Editable Install) ⭐ RECOMMENDED

**Use Case**: Active development, testing changes immediately

```bash
cd /Users/prakharagarwal/AgentDock

# Install common package
uv pip install -e packages/common-py

# Install schema package (depends on common)
uv pip install -e packages/schema

# Verify installation
uv pip list | grep agentdock
# Output:
# agentdock-common    0.1.1    /path/to/packages/common-py
# agentdock-schema    0.1.0    /path/to/packages/schema
```

**Benefits:**
- ✅ Changes to code are immediately available (no reinstall needed)
- ✅ Can edit and test simultaneously
- ✅ Perfect for active development

**How it works:**
- Creates symlinks to source directories
- `import agentdock_common` points to `packages/common-py/agentdock_common/`
- Edit files → changes are live immediately

---

### Method 2: With Development Dependencies

**Use Case**: Running tests, code coverage, linting

```bash
# Install with all dev tools
uv pip install -e "packages/common-py[dev]" -e "packages/schema[dev]"

# Now you can run tests
cd packages/schema
pytest tests/
pytest tests/ --cov=agentdock_schema --cov-report=term-missing
```

**Includes:**
- `pytest` - Testing framework
- `pytest-cov` - Code coverage
- `pyyaml` - YAML support (schema only)
- Any other dev dependencies defined in pyproject.toml

---

### Method 3: Regular Install (Non-Editable)

**Use Case**: Production-like testing, CI/CD

```bash
# Install as regular packages
uv pip install packages/common-py packages/schema

# Verify
uv pip list | grep agentdock
# Output:
# agentdock-common    0.1.1
# agentdock-schema    0.1.0
```

**When to use:**
- Testing deployment scenarios
- CI/CD pipelines
- When you don't need to edit source

**How it works:**
- Copies packages to site-packages
- Need to reinstall after code changes

---

### Method 4: Install All Packages from Script

Create a helper script:

```bash
# install-all.sh
#!/bin/bash

set -e  # Exit on error

echo "🚀 Installing all AgentDock packages..."

# Check if uv is available
if command -v uv &> /dev/null; then
    INSTALLER="uv pip"
else
    INSTALLER="pip"
fi

# Install in dependency order
echo "📦 Installing agentdock-common..."
$INSTALLER install -e packages/common-py

echo "📦 Installing agentdock-schema..."
$INSTALLER install -e packages/schema

# Install dev dependencies
echo "🛠️  Installing dev dependencies..."
$INSTALLER install -e "packages/common-py[dev]" -e "packages/schema[dev]"

echo "✅ Installation complete!"
echo ""
echo "Installed packages:"
$INSTALLER list | grep agentdock
```

**Usage:**
```bash
chmod +x install-all.sh
./install-all.sh
```

---

### Method 5: Using uv sync (Project-wide)

**Use Case**: Reproducible installs, lock file management

```bash
# From project root
cd /Users/prakharagarwal/AgentDock

# Sync all dependencies from uv.lock
uv sync

# This installs:
# - All workspace packages
# - All dependencies
# - Locked versions from uv.lock
```

**Benefits:**
- ✅ Reproducible builds
- ✅ Lock file ensures exact versions
- ✅ Handles dependency resolution automatically

---

## Virtual Environment Setup

### Create New Virtual Environment

```bash
# Using uv (recommended)
cd /Users/prakharagarwal/AgentDock
uv venv

# Or using Python's venv
python3.12 -m venv .venv
```

### Activate Virtual Environment

```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

### Verify Activation

```bash
which python
# Should show: /Users/prakharagarwal/AgentDock/.venv/bin/python

echo $VIRTUAL_ENV
# Should show: /Users/prakharagarwal/AgentDock/.venv
```

---

## Installation Order (Important!)

Always install in dependency order:

```
1. agentdock-common  ← No internal dependencies
   ↓
2. agentdock-schema  ← Depends on common
   ↓
3. Other packages    ← May depend on common and/or schema
```

**Correct:**
```bash
uv pip install -e packages/common-py    # Install first
uv pip install -e packages/schema       # Install second (needs common)
```

**Wrong:**
```bash
uv pip install -e packages/schema       # ❌ Will fail! common not installed
uv pip install -e packages/common-py    # Installing after won't fix it
```

If you installed in wrong order:
```bash
# Uninstall and reinstall in correct order
uv pip uninstall agentdock-schema agentdock-common
uv pip install -e packages/common-py -e packages/schema
```

---

## Verifying Installation

### Check Installed Packages

```bash
# List all agentdock packages
uv pip list | grep agentdock

# Expected output:
# agentdock-common    0.1.1    /path/to/packages/common-py
# agentdock-schema    0.1.0    /path/to/packages/schema
```

### Test Imports

```python
# Test in Python REPL
python

>>> from agentdock_common import ValidationError, SUPPORTED_FRAMEWORKS
>>> print(SUPPORTED_FRAMEWORKS)
['langgraph', 'langchain']

>>> from agentdock_schema import DockSpec
>>> print(DockSpec.__name__)
'DockSpec'

>>> # ✅ Both packages work!
```

### Run Tests

```bash
# Test common package
cd packages/common-py
uv run pytest tests/ -v

# Test schema package
cd packages/schema
uv run pytest tests/ -v --cov=agentdock_schema
```

---

## Troubleshooting

### Problem: "No module named 'agentdock_common'"

**Solution:**
```bash
# 1. Verify installation
uv pip list | grep agentdock-common

# 2. If not installed, install it
uv pip install -e packages/common-py

# 3. Verify Python is using correct environment
which python
# Should be in .venv
```

### Problem: "Could not find a version that satisfies the requirement agentdock-common>=0.1.1"

**Cause:** Schema trying to install common from PyPI (not published yet)

**Solution:** Install common locally first:
```bash
uv pip install -e packages/common-py
uv pip install -e packages/schema
```

### Problem: Changes to code not reflected

**Cause:** Installed in regular mode instead of editable mode

**Solution:** Reinstall with `-e` flag:
```bash
uv pip uninstall agentdock-schema
uv pip install -e packages/schema
```

### Problem: "AttributeError: module 'agentdock_common' has no attribute 'X'"

**Cause:** Outdated installation or import cache

**Solution:**
```bash
# 1. Reinstall package
uv pip install -e packages/common-py --force-reinstall --no-deps

# 2. Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 3. Restart Python interpreter
```

### Problem: Dependency conflicts

**Solution:**
```bash
# Check for conflicts
uv pip check

# View dependency tree
uv pip list --tree

# Recreate environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e packages/common-py -e "packages/schema[dev]"
```

---

## Development Workflow

### Typical Development Setup

```bash
# 1. Clone repository
git clone https://github.com/paritosh0707/AgentDock.git
cd AgentDock

# 2. Create virtual environment
uv venv

# 3. Activate it
source .venv/bin/activate

# 4. Install all packages in dev mode
uv pip install -e packages/common-py -e "packages/schema[dev]"

# 5. Verify
uv pip list | grep agentdock

# 6. Run tests
cd packages/schema
pytest tests/
```

### Making Changes

```bash
# Edit code
vim packages/schema/agentdock_schema/dockfile_v1.py

# Test immediately (no reinstall needed with -e)
cd packages/schema
pytest tests/test_models.py -v

# Changes are live!
```

### Adding New Packages

When creating new packages (e.g., `agentdock-cli`):

```bash
# 1. Add dependency in pyproject.toml
# packages/cli/pyproject.toml
dependencies = [
    "agentdock-common>=0.1.1,<0.2.0",
    "agentdock-schema>=0.1.0,<0.2.0",
]

# 2. Install in order
uv pip install -e packages/common-py
uv pip install -e packages/schema
uv pip install -e packages/cli
```

---

## CI/CD Installation

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install uv
        run: pip install uv
      
      - name: Install packages
        run: |
          uv venv
          source .venv/bin/activate
          uv pip install -e packages/common-py -e "packages/schema[dev]"
      
      - name: Run tests
        run: |
          source .venv/bin/activate
          cd packages/schema
          pytest tests/ --cov=agentdock_schema --cov-report=xml
```

---

## Production Deployment (Future)

When packages are published to PyPI:

```bash
# Regular users will install from PyPI
pip install agentdock-schema

# This automatically installs agentdock-common as dependency
# No need to clone repository
```

**Current workaround** (until published):
```bash
# Package as wheel
cd packages/common-py
python -m build

cd ../schema
python -m build

# Install wheels
pip install packages/common-py/dist/agentdock_common-0.1.1-py3-none-any.whl
pip install packages/schema/dist/agentdock_schema-0.1.0-py3-none-any.whl
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Install all (dev) | `uv pip install -e packages/common-py -e "packages/schema[dev]"` |
| Install all (prod) | `uv pip install -e packages/common-py -e packages/schema` |
| Verify installation | `uv pip list \| grep agentdock` |
| Run tests | `cd packages/schema && pytest tests/` |
| Update dependencies | `cd packages/schema && uv sync` |
| Uninstall all | `uv pip uninstall agentdock-schema agentdock-common` |
| Check conflicts | `uv pip check` |
| List dependencies | `uv pip list --tree` |

---

## Best Practices

1. ✅ **Always use editable install** (`-e`) for development
2. ✅ **Install in dependency order** (common → schema → others)
3. ✅ **Use virtual environments** (never install globally)
4. ✅ **Install dev dependencies** for running tests
5. ✅ **Keep uv.lock in version control** for reproducibility
6. ✅ **Use `uv sync`** to ensure exact versions
7. ✅ **Test after installation** with `pytest`

---

## Summary

**For Development (Most Common):**
```bash
cd /Users/prakharagarwal/AgentDock
source .venv/bin/activate
uv pip install -e packages/common-py -e "packages/schema[dev]"
```

**For Testing:**
```bash
cd packages/schema
pytest tests/ --cov=agentdock_schema
```

**For Production (Future):**
```bash
pip install agentdock-schema  # Will auto-install common
```

---

**Last Updated**: November 12, 2024  
**Python Version**: 3.12+  
**Package Manager**: uv (recommended) or pip

