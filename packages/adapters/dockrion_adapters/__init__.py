"""
dockrion Adapters Package

Provides uniform interface to different agent frameworks (LangGraph, LangChain, etc.)
and custom handler functions, enabling dockrion runtime to invoke any agent type
through a consistent API.

Supports two modes:
1. **Framework Agents** (entrypoint mode): LangGraph, LangChain, etc.
2. **Handler Functions** (handler mode): Direct callable functions

Public API:
    # Protocol
    - AgentAdapter: Protocol defining adapter interface

    # Concrete Adapters
    - LangGraphAdapter: Adapter for LangGraph compiled graphs
    - HandlerAdapter: Adapter for direct callable handler functions

    # Factory
    - get_adapter: Get adapter instance for framework
    - get_handler_adapter: Get adapter for handler functions
    - register_adapter: Register custom adapter
    - list_supported_frameworks: Get list of supported frameworks
    - is_framework_supported: Check if framework is supported

    # Errors
    - AdapterError: Base adapter error
    - AdapterLoadError: Agent loading failed
    - AdapterNotLoadedError: Invoke before load
    - AgentExecutionError: Agent invocation failed
    - InvalidAgentError: Agent missing required interface
    - InvalidOutputError: Agent returned non-dict

Usage:
    from dockrion_adapters import get_adapter, get_handler_adapter

    # Framework agent (entrypoint mode)
    adapter = get_adapter("langgraph")
    adapter.load("examples.invoice_copilot.app.graph:build_graph")
    result = adapter.invoke({"document_text": "INVOICE #123..."})

    # Handler function (handler mode)
    adapter = get_handler_adapter()
    adapter.load("app.service:process_request")
    result = adapter.invoke({"query": "hello"})
"""

# Protocol and base classes
from .base import (
    AgentAdapter,
    AsyncAgentAdapter,
    StatefulAgentAdapter,
    StreamingAgentAdapter,
)

# Error classes
from .errors import (
    AdapterError,
    AdapterLoadError,
    AdapterNotLoadedError,
    AgentCrashedError,
    AgentExecutionError,
    CallableNotFoundError,
    InvalidAgentError,
    InvalidOutputError,
    ModuleNotFoundError,
)
from .handler_adapter import HandlerAdapter

# Concrete adapter implementations
from .langgraph_adapter import LangGraphAdapter

# Factory and registry functions
from .registry import (
    get_adapter,
    get_adapter_info,
    get_handler_adapter,
    is_framework_supported,
    list_supported_frameworks,
    register_adapter,
)

__version__ = "0.1.0"

__all__ = [
    # Protocol
    "AgentAdapter",
    "StreamingAgentAdapter",
    "AsyncAgentAdapter",
    "StatefulAgentAdapter",
    # Adapters
    "LangGraphAdapter",
    "HandlerAdapter",
    # Factory
    "get_adapter",
    "get_handler_adapter",
    "register_adapter",
    "list_supported_frameworks",
    "is_framework_supported",
    "get_adapter_info",
    # Errors
    "AdapterError",
    "AdapterLoadError",
    "ModuleNotFoundError",
    "CallableNotFoundError",
    "InvalidAgentError",
    "AdapterNotLoadedError",
    "AgentExecutionError",
    "AgentCrashedError",
    "InvalidOutputError",
]
