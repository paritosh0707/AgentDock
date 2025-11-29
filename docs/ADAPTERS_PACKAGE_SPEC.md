# Dockrion Adapters Package Specification

**Version:** 1.0  
**Last Updated:** November 14, 2024  
**Status:** Design Document

---

## Table of Contents

1. [Purpose & Overview](#purpose--overview)
2. [Core Concepts](#core-concepts)
3. [Architecture Position](#architecture-position)
4. [Design Principles](#design-principles)
5. [Core Functionalities](#core-functionalities)
6. [LangGraph Adapter Specification](#langgraph-adapter-specification)
7. [API Reference](#api-reference)
8. [Implementation Phases](#implementation-phases)
9. [Testing Strategy](#testing-strategy)
10. [Integration Examples](#integration-examples)
11. [Future Extensions](#future-extensions)
12. [Design Decisions](#design-decisions)

---

## Purpose & Overview

### One-Sentence Summary
**The Adapters package provides a uniform interface to different agent frameworks (LangGraph, LangChain, etc.), enabling Dockrion runtime to invoke any agent type through a consistent API.**

### The Problem It Solves

Different agent frameworks have different interfaces:

```python
# LangGraph
graph = build_graph()
result = graph.invoke({"input": "hello"})

# LangChain
chain = build_chain()
result = chain.run("hello")

# CrewAI (future)
crew = create_crew()
result = crew.kickoff(inputs={"query": "hello"})
```

**Dockrion runtime needs ONE unified way to call agents regardless of framework!**

### The Solution

Adapters act as **translation layers** (middleware) that:
1. **Load** user's agent from entrypoint (dynamic import)
2. **Invoke** agent with standard input/output format
3. **Normalize** errors across frameworks
4. **Extract** metadata for monitoring

```
┌─────────────────────────────────────────────────────┐
│         Dockrion Runtime (Framework Agnostic)      │
│                                                      │
│  adapter = get_adapter(framework)  # ← Factory      │
│  adapter.load(entrypoint)          # ← Load agent   │
│  result = adapter.invoke(payload)  # ← Unified call │
└───────────────────┬─────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │   Adapter Layer       │
        │  (Translation Bridge) │
        └───────────┬───────────┘
                    │
        ┌───────────┴────────────┐
        │                        │
   ┌────▼─────┐          ┌──────▼──────┐
   │LangGraph │          │ LangChain   │
   │ Adapter  │          │  Adapter    │
   └────┬─────┘          └──────┬──────┘
        │                       │
        ▼                       ▼
  ┌──────────┐           ┌──────────┐
  │ User's   │           │ User's   │
  │LangGraph │           │LangChain │
  │  Agent   │           │  Agent   │
  └──────────┘           └──────────┘
```

---

## Core Concepts

### 1. Adapter as Middleware

Adapters sit in the middleware stack but have a **specific, narrow responsibility**:

```
HTTP Request → Runtime → [Middleware Stack] → User Agent
                            ↓
                    ┌───────────────────┐
                    │  1. Auth          │ ← Runtime's job
                    │  2. Validation    │ ← Runtime's job
                    │  3. Rate Limiting │ ← Runtime's job
                    │  ════════════════ │
                    │  4. ADAPTER       │ ← ADAPTER'S JOB!
                    │  ════════════════ │
                    │  5. Policy Engine │ ← Policy package
                    │  6. Telemetry     │ ← Telemetry package
                    └───────────────────┘
```

**Adapter Responsibility:** Framework abstraction ONLY

### 2. The Adapter Pattern

Classic design pattern adapted for AI agents:

```python
# Protocol (Interface)
class AgentAdapter(Protocol):
    """Defines what ALL adapters must implement"""
    def load(self, entrypoint: str) -> None: ...
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...

# Concrete Implementation
class LangGraphAdapter(AgentAdapter):
    """LangGraph-specific implementation"""
    def load(self, entrypoint: str) -> None:
        # LangGraph-specific loading logic
        pass
    
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Call LangGraph's .invoke()
        return self._runner.invoke(payload)

# Factory
def get_adapter(framework: str) -> AgentAdapter:
    """Factory returns appropriate adapter"""
    if framework == "langgraph":
        return LangGraphAdapter()
    elif framework == "langchain":
        return LangChainAdapter()
```

**Benefits:**
- ✅ Runtime code doesn't know about specific frameworks
- ✅ Easy to add new frameworks (just add new adapter)
- ✅ Each adapter encapsulates framework-specific logic
- ✅ Uniform error handling

### 3. Dynamic Agent Loading

User's agent code lives in their project, not in Dockrion:

```python
# User's code (examples/invoice_copilot/app/graph.py)
from langgraph.graph import StateGraph

def build_graph():
    """User's factory function"""
    graph = StateGraph(...)
    # ... build graph
    return graph.compile()

# Adapter loads this dynamically at runtime
adapter.load("examples.invoice_copilot.app.graph:build_graph")
#             ↑ module path              ↑ callable name
```

**Loading Process:**
1. Parse entrypoint string
2. Use `importlib` to import module
3. Get callable (factory function)
4. Call factory to get agent instance
5. Validate agent has required methods (`.invoke()`)
6. Store agent for invocations

---

## Architecture Position

### Package Hierarchy

```
┌─────────────────────────────────────────────────────┐
│                  USER INTERFACES                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │   CLI    │  │   SDK    │  │  Runtime (Gen.)  │  │
│  └─────┬────┘  └────┬─────┘  └────────┬─────────┘  │
└────────┼────────────┼─────────────────┼────────────┘
         │            │                  │
         └────────────┼──────────────────┘
                      │
         ┌────────────▼────────────┐
         │                         │
    ┌────▼─────┐            ┌─────▼──────┐
    │  SCHEMA  │            │  ADAPTERS  │ ← This package
    └────┬─────┘            └─────┬──────┘
         │                        │
         └────────┬───────────────┘
                  │
         ┌────────▼─────────┐
         │     COMMON       │
         └──────────────────┘
```

**Dependencies:**
- **Requires**: `common` (for errors, validation, logging)
- **Optional**: Framework libraries (langgraph, langchain) - only when used
- **Used by**: Generated runtime, SDK (for testing)

### Module Boundaries

**Adapters Package OWNS:**
- ✅ `AgentAdapter` protocol definition
- ✅ Framework-specific adapter implementations
- ✅ Adapter registry/factory (`get_adapter()`)
- ✅ Dynamic agent loading logic
- ✅ Framework error → Dockrion error translation

**Adapters Package DOES NOT Own:**
- ❌ User's agent code (that's user's project)
- ❌ Dockfile configuration (that's `schema`)
- ❌ Policy enforcement (that's `policy-engine`)
- ❌ Telemetry/logging (that's `telemetry`)
- ❌ File I/O (loading agents from files - that's SDK)

---

## Design Principles

### 1. Thin Translation Layer
**Principle:** Adapters should be thin wrappers, not heavy middleware

```python
# ✅ GOOD: Simple translation
def invoke(self, payload: Dict) -> Dict:
    return self._runner.invoke(payload)

# ❌ BAD: Too much logic
def invoke(self, payload: Dict) -> Dict:
    # Validate input (NOT adapter's job - runtime does this)
    # Apply policies (NOT adapter's job - policy-engine does this)
    # Log metrics (NOT adapter's job - telemetry does this)
    result = self._runner.invoke(payload)
    # Transform output (NOT adapter's job unless framework requires it)
    return result
```

### 2. Fail Fast, Fail Clear
**Principle:** Errors should be caught early with clear messages

```python
# At load time (startup)
def load(self, entrypoint: str):
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise AdapterLoadError(
            f"Failed to import module '{module_path}': {e}\n"
            f"Hint: Ensure module is in Python path"
        )
```

**Why:** Runtime fails at startup (not on first request), user gets clear error

### 3. Framework-Agnostic Interface
**Principle:** Protocol should work for ANY agent framework

```python
# Protocol doesn't assume LangGraph specifics
class AgentAdapter(Protocol):
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke agent with input payload.
        
        payload: Dict with any structure (defined by io_schema)
        returns: Dict with any structure (defined by io_schema)
        """
```

**Why:** Easy to add new frameworks without changing runtime

### 4. Zero Runtime Overhead Goal
**Principle:** Adapter should add minimal latency

```python
# Target: <50ms overhead vs direct invocation
# Adapter call: 45ms
# Direct call:   42ms
# Overhead:       3ms ✅
```

### 5. No State Between Invocations (MVP)
**Principle:** Each invocation is independent (for MVP)

```python
# Stateless (MVP)
adapter.invoke({"query": "hello"})  # Independent
adapter.invoke({"query": "world"})  # Independent

# Stateful (Phase 2)
adapter.invoke({"query": "hello"}, thread_id="conv-123")
adapter.invoke({"query": "world"}, thread_id="conv-123")  # Same conversation
```

---

## Core Functionalities

### MVP (Phase 1) - Essential Features

#### 1. Agent Loading
**Purpose:** Dynamically import and initialize user's agent

**API:**
```python
def load(self, entrypoint: str) -> None:
    """
    Load agent from entrypoint.
    
    Args:
        entrypoint: Format "module.path:callable"
                   Example: "app.graph:build_graph"
    
    Raises:
        AdapterLoadError: If loading fails
        
    Examples:
        >>> adapter = LangGraphAdapter()
        >>> adapter.load("examples.invoice_copilot.app.graph:build_graph")
        # Agent loaded and ready
    """
```

**Implementation Steps:**
1. Validate entrypoint format (use `common.validate_entrypoint()`)
2. Split into module path and callable name
3. Import module using `importlib.import_module()`
4. Get callable using `getattr(module, callable_name)`
5. Call factory function to get agent instance
6. Validate agent has required interface (`.invoke()` method)
7. Store agent instance in `self._runner`

**Error Scenarios:**
- ❌ Invalid entrypoint format → `ValidationError`
- ❌ Module not found → `AdapterLoadError` (hint: check Python path)
- ❌ Callable doesn't exist → `AdapterLoadError` (hint: check function name)
- ❌ Factory fails → `AdapterLoadError` (include original error)
- ❌ Agent missing `.invoke()` → `AdapterLoadError` (hint: agent must have invoke method)

---

#### 2. Agent Invocation
**Purpose:** Execute agent with input and return output

**API:**
```python
def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke agent with input payload.
    
    Args:
        payload: Input dictionary (matches io_schema.input)
    
    Returns:
        Output dictionary (matches io_schema.output)
    
    Raises:
        AdapterNotLoadedError: If load() not called
        AgentExecutionError: If agent invocation fails
        
    Examples:
        >>> result = adapter.invoke({
        ...     "document_text": "INVOICE #123...",
        ...     "currency_hint": "USD"
        ... })
        >>> print(result["vendor"])
        'Acme Corp'
    """
```

**Implementation Steps:**
1. Check adapter is loaded (`self._runner is not None`)
2. Log invocation start (debug level)
3. Call framework's invoke method: `self._runner.invoke(payload)`
4. Validate output is dict
5. Log invocation complete
6. Return result

**Error Scenarios:**
- ❌ Adapter not loaded → `AdapterNotLoadedError`
- ❌ Agent crashes → `AgentExecutionError` (preserve stack trace)
- ❌ Timeout → `AgentTimeoutError` (handled by runtime, not adapter)
- ❌ Invalid output type → `AgentExecutionError` (must return dict)

---

#### 3. Metadata Extraction
**Purpose:** Get adapter and agent information

**API:**
```python
def get_metadata(self) -> Dict[str, Any]:
    """
    Get adapter metadata for introspection.
    
    Returns:
        Dict with adapter information
        
    Examples:
        >>> metadata = adapter.get_metadata()
        >>> print(metadata)
        {
            "framework": "langgraph",
            "adapter_version": "0.1.0",
            "loaded": True,
            "agent_type": "CompiledGraph",
            "supports_streaming": True,
            "supports_async": True,
            "entrypoint": "app.graph:build_graph"
        }
    """
```

**Use Cases:**
- Runtime health checks
- Debugging (what agent is loaded?)
- Telemetry (agent type, capabilities)
- API introspection endpoint

---

#### 4. Error Normalization
**Purpose:** Convert framework-specific errors to Dockrion errors

**Error Hierarchy:**
```
DockrionError (from common)
└── AdapterError
    ├── AdapterLoadError
    │   ├── ModuleNotFoundError
    │   ├── CallableNotFoundError
    │   └── InvalidAgentError
    ├── AdapterNotLoadedError
    └── AgentExecutionError
        ├── AgentCrashedError
        └── InvalidOutputError
```

**Implementation:**
```python
def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return self._runner.invoke(payload)
    except ImportError as e:
        raise AdapterLoadError(f"Module import failed: {e}")
    except AttributeError as e:
        raise AdapterLoadError(f"Agent missing invoke method: {e}")
    except Exception as e:
        # Preserve original exception in chain
        raise AgentExecutionError(
            f"Agent invocation failed: {type(e).__name__}: {e}"
        ) from e
```

---

### Phase 2 - Advanced Features

#### 5. Streaming Support
**Purpose:** Stream agent responses for long-running tasks

**API:**
```python
def invoke_stream(self, payload: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """
    Stream agent output chunk by chunk.
    
    Args:
        payload: Input dictionary
        
    Yields:
        Chunks of output as they're generated
        
    Examples:
        >>> for chunk in adapter.invoke_stream(payload):
        ...     print(chunk)
        {'type': 'token', 'content': 'The'}
        {'type': 'token', 'content': ' vendor'}
        {'type': 'result', 'data': {...}}
    """
```

**LangGraph Integration:**
```python
def invoke_stream(self, payload: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Stream using LangGraph's .stream() method"""
    for chunk in self._runner.stream(payload):
        # Transform chunk to standard format
        yield self._normalize_chunk(chunk)
```

**Use Cases:**
- Real-time chat applications
- Long document processing with progress
- Token-by-token LLM streaming
- Intermediate step visualization

---

#### 6. Async Support
**Purpose:** Non-blocking agent invocations

**API:**
```python
async def ainvoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async version of invoke().
    
    Args:
        payload: Input dictionary
        
    Returns:
        Output dictionary
        
    Examples:
        >>> result = await adapter.ainvoke(payload)
    """
```

**Benefits:**
- ✅ Concurrent invocations
- ✅ Better resource utilization
- ✅ Non-blocking I/O operations
- ✅ Works with async frameworks (FastAPI)

---

#### 7. State Management (Conversations)
**Purpose:** Support multi-turn conversations and memory

**API:**
```python
def invoke(self, 
          payload: Dict[str, Any], 
          config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Invoke with optional configuration.
    
    Args:
        payload: Input dictionary
        config: Optional configuration
            - thread_id: Conversation thread identifier
            - checkpoint_id: State checkpoint to resume from
            
    Examples:
        >>> # Start conversation
        >>> result = adapter.invoke(
        ...     {"query": "Hello"},
        ...     config={"thread_id": "conv-123"}
        ... )
        >>> # Continue conversation (has memory)
        >>> result = adapter.invoke(
        ...     {"query": "What did I just say?"},
        ...     config={"thread_id": "conv-123"}
        ... )
    """
```

**LangGraph Integration:**
```python
def invoke(self, payload: Dict, config: Optional[Dict] = None) -> Dict:
    if config:
        # LangGraph supports config with thread_id
        return self._runner.invoke(payload, config=config)
    return self._runner.invoke(payload)
```

---

#### 8. Health Checks
**Purpose:** Verify adapter is working

**API:**
```python
def health_check(self) -> bool:
    """
    Quick health check for adapter.
    
    Returns:
        True if adapter is healthy and responsive
        
    Examples:
        >>> if adapter.health_check():
        ...     print("Adapter ready")
    """
```

**Implementation:**
```python
def health_check(self) -> bool:
    if not self._runner:
        return False
    try:
        # Quick test invocation (no-op)
        self._runner.invoke({"__health_check__": True})
        return True
    except:
        return False
```

---

## LangGraph Adapter Specification

### LangGraph Overview

**What is LangGraph?**
- Framework for building stateful, multi-step agent workflows
- Built on top of LangChain
- Uses graph-based execution model (nodes = steps, edges = transitions)
- Supports state persistence, checkpoints, human-in-the-loop

**Key Interfaces:**
```python
from langgraph.graph import StateGraph

# Build graph
graph = StateGraph(state_schema)
graph.add_node("step1", step1_function)
graph.add_node("step2", step2_function)
graph.add_edge("step1", "step2")
graph.set_entry_point("step1")
graph.set_finish_point("step2")

# Compile to get invocable object
app = graph.compile()

# Invocation methods
result = app.invoke(input)           # Sync
result = await app.ainvoke(input)    # Async
stream = app.stream(input)           # Streaming
stream = await app.astream(input)    # Async streaming
```

### LangGraph Agent Requirements

**What Adapter Expects from User's Agent:**

1. **Factory Function Pattern:**
```python
def build_graph():
    """
    Factory function that builds and returns compiled graph.
    
    Returns:
        Compiled LangGraph app (has .invoke() method)
    """
    graph = StateGraph(...)
    # ... add nodes, edges
    return graph.compile()  # ← Must return compiled app
```

2. **Input/Output Format:**
```python
# Input: Dict (any structure defined by io_schema)
input = {"document_text": "...", "currency_hint": "USD"}

# Output: Dict (any structure defined by io_schema)
output = {
    "vendor": "Acme Corp",
    "invoice_number": "INV-123",
    ...
}
```

3. **Required Methods:**
- ✅ `.invoke(input: dict) -> dict` - REQUIRED
- ⚪ `.stream(input: dict) -> Iterator` - OPTIONAL (Phase 2)
- ⚪ `.ainvoke(input: dict) -> dict` - OPTIONAL (Phase 2)

### LangGraph Adapter Implementation

**Class Structure:**
```python
from typing import Dict, Any, Optional, Iterator
from dockrion_common import get_logger, ValidationError
from .base import AgentAdapter

logger = get_logger("langgraph-adapter")


class LangGraphAdapter(AgentAdapter):
    """
    Adapter for LangGraph compiled graphs.
    
    Supports:
    - Synchronous invocation (MVP)
    - Streaming (Phase 2)
    - Async invocation (Phase 2)
    - State management via config (Phase 2)
    """
    
    def __init__(self):
        self._runner: Optional[Any] = None
        self._entrypoint: Optional[str] = None
        self._supports_streaming: bool = False
        self._supports_async: bool = False
    
    def load(self, entrypoint: str) -> None:
        """Load LangGraph agent from entrypoint"""
        # Implementation in next section
        
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke LangGraph agent"""
        # Implementation in next section
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get adapter metadata"""
        return {
            "framework": "langgraph",
            "adapter_version": "0.1.0",
            "loaded": self._runner is not None,
            "entrypoint": self._entrypoint,
            "agent_type": type(self._runner).__name__ if self._runner else None,
            "supports_streaming": self._supports_streaming,
            "supports_async": self._supports_async,
        }
```

### Configuration Support

**LangGraph Config Format:**
```python
config = {
    "configurable": {
        "thread_id": "conversation-123",      # For state persistence
        "checkpoint_id": "checkpoint-xyz",    # Resume from checkpoint
        "recursion_limit": 25,                # Max graph iterations
        "run_name": "invoice-extraction-001", # For tracing
    }
}

result = app.invoke(input, config=config)
```

**Adapter Support:**
```python
def invoke(self, 
          payload: Dict[str, Any], 
          config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Invoke with optional LangGraph configuration.
    
    Args:
        payload: Input data
        config: Optional LangGraph config
            - thread_id: For conversation memory
            - checkpoint_id: Resume from specific checkpoint
            - recursion_limit: Max iterations (default: 25)
    """
    if self._runner is None:
        raise AdapterNotLoadedError("Call load() before invoke()")
    
    try:
        if config:
            return self._runner.invoke(payload, config=config)
        return self._runner.invoke(payload)
    except Exception as e:
        raise AgentExecutionError(f"LangGraph invocation failed: {e}") from e
```

### Checkpointing & State Persistence

**User's Agent with Checkpointing:**
```python
from langgraph.checkpoint import MemorySaver

def build_graph():
    graph = StateGraph(...)
    # ... add nodes
    
    # Add checkpointer for state persistence
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
```

**Adapter Behavior:**
- ✅ Adapter passes through config with thread_id
- ✅ LangGraph handles state persistence internally
- ❌ Adapter doesn't manage checkpointer (user's responsibility)

**Multi-Turn Example:**
```python
# Turn 1
result = adapter.invoke(
    {"query": "What's the weather?"},
    config={"thread_id": "user-123"}
)

# Turn 2 (has memory of turn 1)
result = adapter.invoke(
    {"query": "What about tomorrow?"},
    config={"thread_id": "user-123"}
)
```

---

## API Reference

### Protocol Definition

```python
from typing import Protocol, Dict, Any, Optional, Iterator

class AgentAdapter(Protocol):
    """
    Protocol defining adapter interface.
    
    All adapter implementations must provide these methods.
    """
    
    def load(self, entrypoint: str) -> None:
        """
        Load agent from entrypoint.
        
        Args:
            entrypoint: Format "module.path:callable"
            
        Raises:
            AdapterLoadError: If loading fails
        """
        ...
    
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke agent with input payload.
        
        Args:
            payload: Input dictionary
            
        Returns:
            Output dictionary
            
        Raises:
            AdapterNotLoadedError: If not loaded
            AgentExecutionError: If invocation fails
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get adapter metadata.
        
        Returns:
            Metadata dictionary
        """
        ...
```

### Factory Function

```python
def get_adapter(framework: str) -> AgentAdapter:
    """
    Get adapter instance for framework.
    
    Args:
        framework: Framework name ("langgraph", "langchain", etc.)
        
    Returns:
        Adapter instance
        
    Raises:
        ValidationError: If framework not supported
        
    Examples:
        >>> adapter = get_adapter("langgraph")
        >>> adapter.load("app.graph:build_graph")
        >>> result = adapter.invoke({"input": "data"})
    """
```

### Error Classes

```python
class AdapterError(DockrionError):
    """Base class for adapter errors"""
    pass

class AdapterLoadError(AdapterError):
    """Raised when agent loading fails"""
    pass

class AdapterNotLoadedError(AdapterError):
    """Raised when invoke called before load"""
    pass

class AgentExecutionError(AdapterError):
    """Raised when agent invocation fails"""
    pass
```

---

## Implementation Phases

### Phase 1: MVP (Week 1-2)

**Goal:** Basic adapter working with LangGraph

**Deliverables:**
- [ ] `base.py` - Protocol definition
- [ ] `langgraph_adapter.py` - Basic implementation
  - [ ] `load()` method
  - [ ] `invoke()` method
  - [ ] `get_metadata()` method
- [ ] `registry.py` - Factory function
- [ ] `errors.py` - Error classes
- [ ] Tests for basic functionality
- [ ] README with usage examples

**Success Criteria:**
- ✅ Can load LangGraph agent from entrypoint
- ✅ Can invoke loaded agent
- ✅ Errors are clear and actionable
- ✅ >80% test coverage

---

### Phase 2: Enhanced Features (Week 3-4)

**Goal:** Add streaming, async, state support

**Deliverables:**
- [ ] Streaming support (`invoke_stream()`)
- [ ] Async support (`ainvoke()`)
- [ ] State management (config with thread_id)
- [ ] Health checks
- [ ] Performance optimizations
- [ ] Comprehensive tests

**Success Criteria:**
- ✅ Streaming works with SSE endpoint
- ✅ Async invocations work
- ✅ Multi-turn conversations maintain state
- ✅ <50ms overhead vs direct invocation

---

### Phase 3: LangChain & Polish (Week 5-6)

**Goal:** Add LangChain support, production-ready

**Deliverables:**
- [ ] `langchain_adapter.py` - LangChain implementation
- [ ] Tool call tracking
- [ ] Comprehensive error handling
- [ ] Performance benchmarks
- [ ] Production-ready documentation
- [ ] Migration guide from raw framework usage

**Success Criteria:**
- ✅ Both LangGraph and LangChain supported
- ✅ Production-tested with real agents
- ✅ Complete documentation
- ✅ Ready for V1 release

---

## Testing Strategy

### Unit Tests

**Test Coverage Areas:**

1. **Protocol Compliance:**
```python
def test_langgraph_adapter_implements_protocol():
    """Verify LangGraphAdapter implements AgentAdapter protocol"""
    adapter = LangGraphAdapter()
    assert isinstance(adapter, AgentAdapter)
```

2. **Loading Success:**
```python
def test_load_valid_agent():
    """Test loading valid LangGraph agent"""
    adapter = LangGraphAdapter()
    adapter.load("tests.fixtures.sample_agent:build_graph")
    assert adapter._runner is not None
```

3. **Loading Failures:**
```python
def test_load_invalid_module():
    """Test error when module doesn't exist"""
    adapter = LangGraphAdapter()
    with pytest.raises(AdapterLoadError) as exc:
        adapter.load("nonexistent.module:build")
    assert "Failed to import" in str(exc.value)

def test_load_missing_callable():
    """Test error when callable doesn't exist"""
    adapter = LangGraphAdapter()
    with pytest.raises(AdapterLoadError) as exc:
        adapter.load("tests.fixtures:nonexistent_function")
    assert "no function" in str(exc.value).lower()
```

4. **Invocation Success:**
```python
def test_invoke_returns_dict():
    """Test successful invocation returns dict"""
    adapter = LangGraphAdapter()
    adapter.load("tests.fixtures.sample_agent:build_graph")
    
    result = adapter.invoke({"input": "test"})
    
    assert isinstance(result, dict)
    assert "output" in result
```

5. **Invocation Failures:**
```python
def test_invoke_before_load():
    """Test error when invoking before loading"""
    adapter = LangGraphAdapter()
    with pytest.raises(AdapterNotLoadedError):
        adapter.invoke({"input": "test"})
```

6. **Metadata Extraction:**
```python
def test_metadata():
    """Test metadata extraction"""
    adapter = LangGraphAdapter()
    adapter.load("tests.fixtures.sample_agent:build_graph")
    
    metadata = adapter.get_metadata()
    
    assert metadata["framework"] == "langgraph"
    assert metadata["loaded"] is True
    assert "agent_type" in metadata
```

### Integration Tests

**Test with Real Agents:**

```python
def test_invoice_copilot_integration():
    """Test with actual invoice copilot agent"""
    adapter = get_adapter("langgraph")
    adapter.load("examples.invoice_copilot.app.graph:build_graph")
    
    result = adapter.invoke({
        "document_text": "INVOICE #123 from Acme Corp...",
        "currency_hint": "USD"
    })
    
    assert result["vendor"] == "Acme Corp"
    assert "invoice_number" in result
```

### Performance Tests

```python
def test_adapter_overhead():
    """Measure adapter overhead"""
    import time
    
    adapter = LangGraphAdapter()
    adapter.load("tests.fixtures.sample_agent:build_graph")
    
    # Direct invocation
    direct_start = time.time()
    adapter._runner.invoke({"input": "test"})
    direct_time = time.time() - direct_start
    
    # Via adapter
    adapter_start = time.time()
    adapter.invoke({"input": "test"})
    adapter_time = time.time() - adapter_start
    
    overhead = adapter_time - direct_time
    assert overhead < 0.05  # <50ms overhead
```

### Test Fixtures

**Create sample agents for testing:**

```python
# tests/fixtures/sample_agent.py

def build_graph():
    """Simple test agent"""
    class TestAgent:
        def invoke(self, payload):
            return {"output": f"Processed: {payload.get('input')}"}
    return TestAgent()

def build_stateful_graph():
    """Test agent with state"""
    class StatefulAgent:
        def __init__(self):
            self.state = {}
        
        def invoke(self, payload, config=None):
            thread_id = config.get("thread_id") if config else None
            if thread_id:
                # Simulate state persistence
                self.state[thread_id] = payload
            return {"output": "success", "state_saved": thread_id is not None}
    return StatefulAgent()
```

---

## Integration Examples

### Example 1: Runtime Integration

```python
# Generated runtime.py

from dockrion_adapters import get_adapter
from dockrion_common import success_response, error_response

# Load adapter at startup
FRAMEWORK = "langgraph"
ENTRYPOINT = "examples.invoice_copilot.app.graph:build_graph"

adapter = get_adapter(FRAMEWORK)
adapter.load(ENTRYPOINT)

@app.post("/invoke")
async def invoke(request: Request):
    """Invoke endpoint using adapter"""
    try:
        payload = await request.json()
        result = adapter.invoke(payload)
        return success_response(result)
    except AgentExecutionError as e:
        return JSONResponse(
            status_code=500,
            content=error_response(e)
        )
```

### Example 2: SDK Testing Integration

```python
# SDK can use adapters to test agents locally

from dockrion_adapters import get_adapter
from dockrion_schema import DockSpec

def test_agent_locally(dockspec: DockSpec):
    """Test agent before deployment"""
    adapter = get_adapter(dockspec.agent.framework)
    adapter.load(dockspec.agent.entrypoint)
    
    # Test with sample input
    test_input = {"test": "data"}
    result = adapter.invoke(test_input)
    
    print(f"✅ Agent works! Output: {result}")
```

### Example 3: Multi-Framework Support

```python
# Runtime can handle any framework

FRAMEWORK = os.getenv("AGENT_FRAMEWORK", "langgraph")

# Factory returns appropriate adapter
adapter = get_adapter(FRAMEWORK)  

# Rest of code is identical regardless of framework
adapter.load(ENTRYPOINT)
result = adapter.invoke(payload)
```

---

## Future Extensions

### V2 Features

#### 1. Custom Adapters (Plugins)
```python
# Users can register custom adapters
from dockrion_adapters import register_adapter

class MyCustomAdapter(AgentAdapter):
    def load(self, entrypoint): ...
    def invoke(self, payload): ...

register_adapter("custom", MyCustomAdapter)
```

#### 2. Adapter Middleware/Hooks
```python
class LangGraphAdapter:
    def __init__(self):
        self._pre_invoke_hooks = []
        self._post_invoke_hooks = []
    
    def add_pre_hook(self, hook):
        """Add hook to run before invocation"""
        self._pre_invoke_hooks.append(hook)
    
    def invoke(self, payload):
        # Run pre hooks
        for hook in self._pre_invoke_hooks:
            payload = hook(payload)
        
        result = self._runner.invoke(payload)
        
        # Run post hooks
        for hook in self._post_invoke_hooks:
            result = hook(result)
        
        return result
```

#### 3. Tool Call Interception
```python
def invoke(self, payload):
    """Invoke with tool call tracking"""
    result = self._runner.invoke(payload)
    
    # Extract tool calls from LangGraph execution
    if hasattr(result, '_tool_calls'):
        return {
            "output": result.output,
            "metadata": {
                "tools_called": result._tool_calls,
                "tool_durations": result._tool_durations
            }
        }
    return result
```

#### 4. Multi-Agent Orchestration
```python
class MultiAgentAdapter:
    """Adapter that coordinates multiple agents"""
    def __init__(self):
        self._agents = {}
    
    def load_agent(self, name: str, entrypoint: str):
        adapter = get_adapter("langgraph")
        adapter.load(entrypoint)
        self._agents[name] = adapter
    
    def invoke(self, payload):
        # Route to appropriate agent or coordinate multiple
        agent_name = payload.get("agent")
        return self._agents[agent_name].invoke(payload)
```

---

## Design Decisions

### Decision Record

#### DR-1: Protocol vs Abstract Base Class

**Decision:** Use Protocol for interface definition

**Rationale:**
- ✅ More Pythonic (duck typing)
- ✅ No forced inheritance
- ✅ Easier for users to extend
- ✅ Runtime type checking with `isinstance()`

**Alternatives Considered:**
- Abstract Base Class (ABC) - Too rigid, forces inheritance

---

#### DR-2: Eager vs Lazy Loading

**Decision:** Eager loading (load at startup)

**Rationale:**
- ✅ Fail fast - errors caught at startup, not first request
- ✅ No latency on first invocation
- ✅ Simpler code
- ✅ More predictable behavior

**Alternatives Considered:**
- Lazy loading - Would be faster startup but unpredictable first request

---

#### DR-3: Stateless vs Stateful Adapter

**Decision:** Stateless in MVP, stateful in Phase 2

**Rationale:**
- ✅ MVP: Simpler, fewer edge cases
- ✅ Phase 2: Add config parameter for thread_id
- ✅ Gradual complexity increase

**Alternatives Considered:**
- Stateful from start - Too complex for MVP

---

#### DR-4: Error Handling Strategy

**Decision:** Selective error wrapping with chain

**Rationale:**
- ✅ Preserves original stack traces (`raise ... from e`)
- ✅ Clear error messages
- ✅ Framework-specific details available for debugging

**Example:**
```python
try:
    result = self._runner.invoke(payload)
except LangGraphError as e:
    raise AgentExecutionError(f"LangGraph error: {e}") from e
    #                                                      ↑ preserves chain
```

**Alternatives Considered:**
- Wrap all exceptions - Loses important debugging info
- Don't wrap - Leaks framework details to runtime

---

#### DR-5: Timeout Handling Location

**Decision:** Runtime handles timeouts, not adapter

**Rationale:**
- ✅ Runtime has more control (can kill thread)
- ✅ Adapter stays simple
- ✅ Timeout policy is deployment-level, not adapter-level

**Implementation:**
```python
# Runtime wraps adapter call
import asyncio

try:
    result = await asyncio.wait_for(
        adapter.invoke(payload),
        timeout=30  # Runtime's timeout
    )
except asyncio.TimeoutError:
    raise InvocationTimeoutError()
```

---

## Dependencies

### Required

```toml
[project]
dependencies = [
    "dockrion-common>=0.1.0",  # For errors, validation, logging
]
```

### Optional (Framework-specific)

```toml
[project.optional-dependencies]
langgraph = [
    "langgraph>=0.0.20",
    "langchain-core>=0.1.0"
]

langchain = [
    "langchain>=0.1.0"
]

all = [
    "langgraph>=0.0.20",
    "langchain>=0.1.0"
]
```

### Installation

```bash
# Minimal (just protocol and common)
pip install dockrion-adapters

# With LangGraph support
pip install dockrion-adapters[langgraph]

# With all frameworks
pip install dockrion-adapters[all]
```

---

## File Structure

```
packages/adapters/
├── dockrion_adapters/
│   ├── __init__.py           # Public API exports
│   ├── base.py               # AgentAdapter protocol
│   ├── langgraph_adapter.py  # LangGraph implementation
│   ├── langchain_adapter.py  # LangChain (Phase 3)
│   ├── registry.py           # get_adapter() factory
│   └── errors.py             # Adapter-specific errors
├── tests/
│   ├── __init__.py
│   ├── test_langgraph_adapter.py
│   ├── test_registry.py
│   ├── test_integration.py
│   └── fixtures/
│       └── sample_agents.py
├── pyproject.toml
└── README.md
```

---

## Summary

### Key Takeaways

1. **Adapters = Framework Abstraction Layer**
   - Not security, not policy, not logging
   - Just framework translation

2. **Two Responsibilities:**
   - Load user's agent dynamically
   - Invoke agent uniformly

3. **Design Principles:**
   - Thin translation layer
   - Fail fast with clear errors
   - Framework-agnostic interface
   - Zero state (MVP)

4. **Implementation Phases:**
   - Phase 1: Basic LangGraph (2 weeks)
   - Phase 2: Advanced features (2 weeks)
   - Phase 3: LangChain + polish (2 weeks)

5. **Success Metrics:**
   - <50ms overhead
   - >80% test coverage
   - Clear error messages
   - Works with real agents

---

## Next Steps

1. **Review & Approve** this specification
2. **Create `base.py`** with Protocol definition
3. **Implement `langgraph_adapter.py`** (MVP features only)
4. **Write tests** as you implement
5. **Test with invoice_copilot** example
6. **Iterate** based on feedback

---

**Document Owner:** Dockrion Development Team  
**Last Review:** November 14, 2024  
**Next Review:** After Phase 1 completion

