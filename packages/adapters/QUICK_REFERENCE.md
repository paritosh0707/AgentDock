# AgentDock Adapters - Quick Reference

## 🚀 30-Second Start

```python
from agentdock_adapters import get_adapter

adapter = get_adapter("langgraph")
adapter.load("app.graph:build_graph")
result = adapter.invoke({"input": "test"})
```

---

## 📦 What's in the Box?

### Core Modules (5 files)

| File | What It Does | Key Items |
|------|--------------|-----------|
| `base.py` | Protocol definitions | `AgentAdapter` + 3 future protocols |
| `errors.py` | Error hierarchy | 9 error classes with hints |
| `langgraph_adapter.py` | LangGraph impl | Load, invoke, metadata, health |
| `registry.py` | Factory & registry | 5 functions for framework mgmt |
| `__init__.py` | Public API | 15 exports |

### Test Suite (45 tests)

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `test_langgraph_adapter.py` | 28 | Loading, invoking, metadata, health, errors |
| `test_registry.py` | 17 | Factory, registration, listing |

### Documentation (4 docs)

| Document | Purpose |
|----------|---------|
| `README.md` | User guide with examples |
| `IMPLEMENTATION_SUMMARY.md` | Technical deep dive |
| `IMPLEMENTATION_COMPLETE.md` | Completion status |
| `QUICK_REFERENCE.md` | This cheat sheet |

---

## 🎯 API Cheat Sheet

### Get Adapter
```python
from agentdock_adapters import get_adapter

adapter = get_adapter("langgraph")  # or "langchain" (Phase 2)
```

### Load Agent
```python
# Format: "module.path:callable"
adapter.load("examples.invoice_copilot.app.graph:build_graph")
```

### Invoke Agent
```python
result = adapter.invoke({
    "input_field": "value"
})
# Returns: {"output_field": "value"}
```

### Get Metadata
```python
metadata = adapter.get_metadata()
# {
#   "framework": "langgraph",
#   "loaded": True,
#   "agent_type": "CompiledGraph",
#   "entrypoint": "app.graph:build_graph",
#   "supports_streaming": False,
#   "supports_async": False
# }
```

### Health Check
```python
if adapter.health_check():
    print("Ready!")
```

---

## ⚠️ Error Handling

### Common Errors

```python
from agentdock_adapters import (
    AdapterLoadError,        # Loading failed
    AdapterNotLoadedError,   # Invoke before load
    AgentExecutionError,     # Agent crashed
)

try:
    adapter.load("app.graph:build")
except AdapterLoadError as e:
    print(f"Load failed: {e}")

try:
    result = adapter.invoke(payload)
except AgentExecutionError as e:
    print(f"Execution failed: {e}")
```

### Error Hierarchy
```
AdapterError
├── AdapterLoadError
│   ├── ModuleNotFoundError      # Module import failed
│   ├── CallableNotFoundError    # Function not in module
│   └── InvalidAgentError        # Agent missing .invoke()
├── AdapterNotLoadedError         # Called invoke before load
└── AgentExecutionError          # Agent crashed
    ├── AgentCrashedError        # Runtime error
    └── InvalidOutputError       # Returned non-dict
```

---

## 🏭 Registry Functions

```python
from agentdock_adapters import (
    get_adapter,              # Get adapter instance
    register_adapter,         # Register custom adapter
    list_supported_frameworks, # List all frameworks
    is_framework_supported,   # Check if framework supported
    get_adapter_info,         # Get adapter metadata
)

# List frameworks
frameworks = list_supported_frameworks()
# ['langgraph']

# Check support
if is_framework_supported("langgraph"):
    adapter = get_adapter("langgraph")

# Get info
info = get_adapter_info("langgraph")
# {'framework': 'langgraph', 'adapter_class': 'LangGraphAdapter', ...}

# Register custom
class MyAdapter:
    def load(self, entrypoint): ...
    def invoke(self, payload): ...
    def get_metadata(self): ...

register_adapter("myframework", MyAdapter)
```

---

## 🧪 Testing Commands

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_langgraph_adapter.py -v

# Run with coverage
uv run pytest tests/ --cov=agentdock_adapters --cov-report=term-missing

# Run single test
uv run pytest tests/test_langgraph_adapter.py::TestLoading::test_load_simple_agent -v
```

---

## 📊 Current Status

| Feature | Status |
|---------|--------|
| Protocol Definition | ✅ Complete |
| LangGraph Adapter | ✅ Complete |
| Error Handling | ✅ Complete |
| Factory Pattern | ✅ Complete |
| Tests (45) | ✅ 100% passing |
| Documentation | ✅ Complete |
| Type Hints | ✅ Complete |
| Logging | ✅ Complete |

---

## 🔮 What's Next? (Phase 2)

```python
# Streaming (Phase 2)
for chunk in adapter.invoke_stream(payload):
    print(chunk)

# Async (Phase 2)
result = await adapter.ainvoke(payload)

# State Management (Phase 2)
result = adapter.invoke(
    payload,
    config={"thread_id": "conv-123"}
)
```

---

## 📁 File Structure

```
packages/adapters/
├── agentdock_adapters/      # Source code
│   ├── __init__.py          # Public API
│   ├── base.py              # Protocols
│   ├── errors.py            # Errors
│   ├── langgraph_adapter.py # LangGraph impl
│   └── registry.py          # Factory
├── tests/                   # Tests
│   ├── fixtures/
│   │   └── sample_agents.py # Mock agents
│   ├── test_langgraph_adapter.py
│   └── test_registry.py
├── examples/                # Examples
│   ├── basic_usage.py
│   └── standalone_demo.py
├── pyproject.toml           # Package config
├── README.md                # Main docs
├── IMPLEMENTATION_SUMMARY.md
├── IMPLEMENTATION_COMPLETE.md
└── QUICK_REFERENCE.md       # This file
```

---

## 🎓 Quick Tips

### Agent Requirements
Your agent must:
1. Have a factory function that returns an object
2. The object must have `.invoke(dict) -> dict` method
3. Input and output must be dictionaries

```python
# Good ✅
def build_graph():
    graph = StateGraph(...)
    return graph.compile()  # Has .invoke()

# Bad ❌
def build_graph():
    return StateGraph(...)  # No .invoke() method
```

### Entrypoint Format
```python
# Format: "module.path:callable_name"
adapter.load("examples.invoice_copilot.app.graph:build_graph")
#          └─────────┬──────────────┘    └────┬─────┘
#              module path              callable name
```

### Error Messages Have Hints
```python
try:
    adapter.load("app.graph:build")
except ModuleNotFoundError as e:
    # Error includes: "Hint: Ensure module is in Python path"
    print(e)  # Full helpful message
```

---

## 🔗 Useful Links

- **Full README**: `README.md`
- **Technical Deep Dive**: `IMPLEMENTATION_SUMMARY.md`
- **Completion Status**: `IMPLEMENTATION_COMPLETE.md`
- **Spec Document**: `../../docs/ADAPTERS_PACKAGE_SPEC.md`

---

## 💻 Installation

```bash
# From workspace root
cd packages/adapters

# Install package
uv sync

# Install with LangGraph
uv sync --extra langgraph

# Install dev dependencies
uv sync --extra dev
```

---

**Quick Reference v1.0** | Updated: Nov 14, 2025

