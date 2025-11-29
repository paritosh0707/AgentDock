# Dockrion Adapters Package

**Framework abstraction layer for Dockrion**

Provides uniform interface to different agent frameworks (LangGraph, LangChain, etc.), enabling Dockrion runtime to invoke any agent type through a consistent API.

---

## 🎯 Purpose

Different AI agent frameworks have different interfaces. Adapters solve this by providing a **single, unified interface**:

```python
# Regardless of framework...
adapter = get_adapter(framework)  # "langgraph", "langchain", etc.
adapter.load(entrypoint)          # Load user's agent
result = adapter.invoke(payload)  # Invoke with standard input/output
```

## 🚀 Quick Start

### Installation

```bash
# Install from workspace
cd packages/adapters
pip install -e .

# With framework support
pip install -e ".[langgraph]"  # LangGraph support
pip install -e ".[langchain]"  # LangChain support
pip install -e ".[all]"         # All frameworks
```

### Basic Usage

```python
from dockrion_adapters import get_adapter

# 1. Get adapter for framework
adapter = get_adapter("langgraph")

# 2. Load your agent
adapter.load("examples.invoice_copilot.app.graph:build_graph")

# 3. Invoke with input
result = adapter.invoke({
    "document_text": "INVOICE #123...",
    "currency_hint": "USD"
})

print(result)
# {'vendor': 'Acme Corp', 'invoice_number': 'INV-123', ...}
```

### Advanced: Strict Validation & Config Support

```python
from dockrion_adapters import LangGraphAdapter

# Enable strict type validation (requires langgraph installed)
adapter = LangGraphAdapter(strict_validation=True)
adapter.load("app.graph:build_graph")

# Invoke with config for state persistence
result = adapter.invoke(
    {"query": "Hello"},
    config={"thread_id": "user-123"}  # Multi-turn conversation
)

# Next invocation remembers previous context
result = adapter.invoke(
    {"query": "What did I say?"},
    config={"thread_id": "user-123"}  # Same thread
)
```

---

## 📚 Core Concepts

### The Adapter Pattern

Adapters act as **translation layers** between Dockrion and various frameworks:

```
┌──────────────────────────────────────┐
│      Dockrion Runtime               │
│  (Framework Agnostic)                │
└────────────┬─────────────────────────┘
             │
             ▼
    ┌────────────────┐
    │ Adapter Layer  │
    └────────┬───────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐      ┌────▼─────┐
│LangGraph│      │LangChain │
│Adapter  │      │ Adapter  │
└───┬────┘      └────┬─────┘
    │                │
    ▼                ▼
  User's          User's
  Agent           Agent
```

### What Adapters Do

✅ **Load agents** dynamically from entrypoint  
✅ **Invoke agents** with standard dict input/output  
✅ **Normalize errors** across frameworks  
✅ **Extract metadata** for monitoring  

### What Adapters DON'T Do

❌ Security (auth, rate limiting) - Runtime's job  
❌ Policy enforcement - Policy-engine's job  
❌ Logging/metrics - Telemetry's job  
❌ File I/O - SDK's job  

---

## 🎯 Validation Modes

### Duck Typing (Default)

**Best for:** Development, flexibility, no framework dependencies

```python
# No LangGraph installation required
adapter = LangGraphAdapter()  # strict_validation=False (default)
adapter.load("app.graph:build_graph")
```

✅ **Advantages:**
- No framework dependency required
- Works with any agent that has `.invoke()` method
- Fast and flexible
- Easy testing with mocks

⚠️ **Limitations:**
- No type safety
- Won't catch framework-specific errors early

### Strict Validation (Optional)

**Best for:** Production, type safety, catching errors early

```python
# Requires langgraph installed
adapter = LangGraphAdapter(strict_validation=True)
adapter.load("app.graph:build_graph")
```

✅ **Advantages:**
- Validates actual LangGraph types (Pregel, CompiledStateGraph)
- Catches errors at load time
- Type-safe
- Better error messages

⚠️ **Requirements:**
- Requires `langgraph` package installed
- Only works with real LangGraph agents

### Hybrid Approach (Recommended)

```python
import os

# Use strict validation in production, duck typing in dev
strict = os.getenv("ENV") == "production"
adapter = LangGraphAdapter(strict_validation=strict)
```

---

## 🔧 Config Parameter Support

### What is Config?

LangGraph agents can accept an optional `config` parameter for:
- **State persistence** (thread_id for multi-turn conversations)
- **Checkpointing** (resume from specific checkpoint)
- **Recursion limits** (max graph iterations)
- **Tracing** (run_name for debugging)

### Basic Usage

```python
# Simple invocation (no config)
result = adapter.invoke({"query": "Hello"})

# With config for state persistence
result = adapter.invoke(
    {"query": "Hello"},
    config={"thread_id": "user-123"}
)
```

### Multi-Turn Conversations

```python
# Turn 1
result = adapter.invoke(
    {"query": "My name is Alice"},
    config={"thread_id": "conv-1"}
)

# Turn 2 - agent remembers Alice
result = adapter.invoke(
    {"query": "What's my name?"},
    config={"thread_id": "conv-1"}
)
# Agent has context from turn 1!
```

### Config Options

```python
config = {
    "thread_id": "user-123",           # State persistence
    "checkpoint_id": "checkpoint-xyz",  # Resume from checkpoint
    "recursion_limit": 50,              # Max iterations
    "run_name": "invoice-process-001",  # For tracing
}

result = adapter.invoke(payload, config=config)
```

### Automatic Detection

Adapter automatically detects if agent supports config:

```python
adapter.load("app.graph:build_graph")

metadata = adapter.get_metadata()
if metadata["supports_config"]:
    print("✅ Agent supports config parameter")
else:
    print("⚠️ Agent doesn't support config")
```

---

## 🔧 API Reference

### AgentAdapter Protocol

All adapters implement this interface:

```python
from typing import Protocol, Dict, Any

class AgentAdapter(Protocol):
    def load(self, entrypoint: str) -> None:
        """Load agent from entrypoint (module.path:callable)"""
        ...
    
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke agent with input, return output"""
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get adapter metadata for introspection"""
        ...
```

### Factory Function

```python
def get_adapter(framework: str) -> AgentAdapter:
    """
    Get adapter instance for framework.
    
    Args:
        framework: "langgraph", "langchain", etc.
        
    Returns:
        Adapter instance
        
    Raises:
        ValidationError: If framework not supported
    """
```

---

## 💡 Usage Examples

### Example 1: Basic Invocation

```python
from dockrion_adapters import get_adapter

# Load LangGraph agent
adapter = get_adapter("langgraph")
adapter.load("app.graph:build_graph")

# Invoke with data
result = adapter.invoke({"query": "Extract invoice data..."})
print(result["vendor"])
```

### Example 2: Error Handling

```python
from dockrion_adapters import get_adapter
from dockrion_adapters.errors import AdapterLoadError, AgentExecutionError

adapter = get_adapter("langgraph")

try:
    adapter.load("app.graph:build_graph")
except AdapterLoadError as e:
    print(f"Failed to load agent: {e.message}")
    exit(1)

try:
    result = adapter.invoke({"query": "test"})
except AgentExecutionError as e:
    print(f"Agent crashed: {e.message}")
```

### Example 3: Metadata Introspection

```python
adapter = get_adapter("langgraph")
adapter.load("app.graph:build_graph")

# Get adapter info
metadata = adapter.get_metadata()
print(f"Framework: {metadata['framework']}")
print(f"Agent type: {metadata['agent_type']}")
print(f"Supports streaming: {metadata['supports_streaming']}")
```

### Example 4: Multi-Framework Support

```python
def invoke_any_agent(framework: str, entrypoint: str, payload: dict):
    """Generic function that works with any framework"""
    adapter = get_adapter(framework)
    adapter.load(entrypoint)
    return adapter.invoke(payload)

# Works with LangGraph
result = invoke_any_agent("langgraph", "app.lg:build", payload)

# Also works with LangChain
result = invoke_any_agent("langchain", "app.lc:build", payload)
```

---

## 🏗️ Architecture

### Package Structure

```
dockrion_adapters/
├── __init__.py           # Public API
├── base.py               # AgentAdapter protocol
├── langgraph_adapter.py  # LangGraph implementation
├── langchain_adapter.py  # LangChain implementation (Phase 2)
├── registry.py           # get_adapter() factory
└── errors.py             # Error classes
```

### Design Principles

1. **Thin Translation Layer** - Minimal overhead
2. **Fail Fast, Fail Clear** - Errors caught early with actionable messages
3. **Framework-Agnostic Interface** - Protocol works for any framework
4. **Zero Runtime Overhead Goal** - <50ms vs direct invocation

---

## 🧪 Testing

### Run Tests

```bash
cd packages/adapters
pytest tests/ -v
```

### Test Coverage

```bash
pytest tests/ --cov=dockrion_adapters --cov-report=html
```

### Test with Real Agent

```bash
# Test with invoice_copilot example
pytest tests/test_integration.py -v -k invoice
```

---

## 🔌 LangGraph Integration

### What Your Agent Needs

**1. Factory Function Pattern:**
```python
def build_graph():
    """Must return object with .invoke() method"""
    from langgraph.graph import StateGraph
    
    graph = StateGraph(...)
    # ... build graph
    return graph.compile()  # ← Returns compiled app
```

**2. Input/Output as Dicts:**
```python
# Input
{"document_text": "...", "currency": "USD"}

# Output
{"vendor": "Acme", "total": 1234.56}
```

**3. Required Method:**
```python
# Your compiled graph must have:
.invoke(input: dict) -> dict
```

### LangGraph Features Supported

| Feature | MVP (Phase 1) | Phase 2 | Phase 3 |
|---------|---------------|---------|---------|
| Sync invocation | ✅ | ✅ | ✅ |
| Async invocation | ❌ | ✅ | ✅ |
| Streaming | ❌ | ✅ | ✅ |
| State persistence (thread_id) | ❌ | ✅ | ✅ |
| Checkpointing | ❌ | ✅ | ✅ |

### Example LangGraph Agent

```python
# examples/invoice_copilot/app/graph.py

from langgraph.graph import StateGraph

def build_graph():
    """Build invoice extraction agent"""
    
    # Define state
    class State(TypedDict):
        input: str
        output: dict
    
    # Build graph
    graph = StateGraph(State)
    graph.add_node("extract", extract_data)
    graph.add_node("validate", validate_output)
    graph.add_edge("extract", "validate")
    graph.set_entry_point("extract")
    graph.set_finish_point("validate")
    
    # Compile and return
    return graph.compile()

# Adapter loads this:
adapter.load("examples.invoice_copilot.app.graph:build_graph")
```

---

## 🚧 Roadmap

### Phase 1: MVP (Weeks 1-2) ✅
- [x] Protocol definition
- [x] LangGraph adapter (sync)
- [x] Factory function
- [x] Error handling
- [x] Basic tests

### Phase 2: Enhanced Features (Weeks 3-4)
- [ ] Streaming support
- [ ] Async invocation
- [ ] State management (thread_id)
- [ ] Health checks
- [ ] Performance optimizations

### Phase 3: Multi-Framework (Weeks 5-6)
- [ ] LangChain adapter
- [ ] Tool call tracking
- [ ] Production testing
- [ ] Complete documentation

---

## ⚠️ Error Handling

### Error Hierarchy

```
AdapterError
├── AdapterLoadError
│   ├── ModuleNotFoundError
│   ├── CallableNotFoundError
│   └── InvalidAgentError
├── AdapterNotLoadedError
└── AgentExecutionError
    ├── AgentCrashedError
    └── InvalidOutputError
```

### Common Errors

**1. Module Not Found**
```python
AdapterLoadError: Failed to import module 'app.graph': No module named 'app'
Hint: Ensure module is in Python path
```

**2. Callable Not Found**
```python
AdapterLoadError: Module 'app.graph' has no function 'build_graph'
Hint: Check function name in entrypoint
```

**3. Agent Missing invoke()**
```python
InvalidAgentError: Agent must have .invoke() method. Got type: MyAgent
Hint: Ensure your factory returns object with .invoke(dict) -> dict
```

**4. Invoke Before Load**
```python
AdapterNotLoadedError: Adapter not loaded. Call .load(entrypoint) first.
```

---

## 📖 Documentation

- **Full Specification**: [docs/ADAPTERS_PACKAGE_SPEC.md](../../docs/ADAPTERS_PACKAGE_SPEC.md)
- **Package Responsibilities**: [docs/PACKAGE_RESPONSIBILITIES.md](../../docs/PACKAGE_RESPONSIBILITIES.md)
- **Developer Journey**: [docs/DEVELOPER_JOURNEY.md](../../docs/DEVELOPER_JOURNEY.md)

---

## 🤝 Contributing

### Adding a New Framework

1. **Implement the protocol:**
```python
# dockrion_adapters/myframework_adapter.py

from .base import AgentAdapter

class MyFrameworkAdapter(AgentAdapter):
    def load(self, entrypoint: str) -> None:
        # Framework-specific loading
        pass
    
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Framework-specific invocation
        pass
```

2. **Register in factory:**
```python
# dockrion_adapters/registry.py

_ADAPTERS = {
    "langgraph": LangGraphAdapter,
    "langchain": LangChainAdapter,
    "myframework": MyFrameworkAdapter,  # ← Add here
}
```

3. **Add tests:**
```python
# tests/test_myframework_adapter.py

def test_myframework_adapter():
    adapter = get_adapter("myframework")
    # ... test load and invoke
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific adapter
pytest tests/test_langgraph_adapter.py -v

# With coverage
pytest tests/ --cov=dockrion_adapters --cov-report=term-missing
```

---

## 🐛 Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError` when loading agent

**Solution:**
```bash
# Ensure your agent's module is in Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/your/project"

# Or install your package
pip install -e /path/to/your/project
```

### Agent Missing invoke()

**Problem:** `InvalidAgentError: Agent must have .invoke() method`

**Solution:**
```python
# Ensure your factory returns object with .invoke()
def build_graph():
    graph = StateGraph(...)
    return graph.compile()  # ← Must return compiled app
    
# Not:
def build_graph():
    return StateGraph(...)  # ❌ Un-compiled graph won't work
```

### Performance Issues

**Problem:** Adapter adds significant overhead

**Check:**
```python
import time

# Measure direct invocation
start = time.time()
compiled_app.invoke(payload)
direct_time = time.time() - start

# Measure via adapter
start = time.time()
adapter.invoke(payload)
adapter_time = time.time() - start

overhead = adapter_time - direct_time
print(f"Overhead: {overhead*1000:.1f}ms")
```

**Target:** <50ms overhead

---

## 📝 License

See repository LICENSE file.

---

## 🔗 Related Packages

- **common**: Error classes, validation, logging
- **schema**: Dockfile validation
- **sdk**: Deployment orchestration
- **runtime**: Generated runtime servers

---

**Maintained by:** Dockrion Development Team  
**Issues:** [GitHub Issues](https://github.com/paritosh0707/Dockrion/issues)  
**Slack:** #dockrion-dev

