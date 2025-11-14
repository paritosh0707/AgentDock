"""
AgentDock Adapters Package

Provides uniform interface to different agent frameworks (LangGraph, LangChain, etc.),
enabling AgentDock runtime to invoke any agent type through a consistent API.

Public API:
    # Protocol
    - AgentAdapter: Protocol defining adapter interface
    
    # Concrete Adapters
    - LangGraphAdapter: Adapter for LangGraph compiled graphs
    
    # Factory
    - get_adapter: Get adapter instance for framework
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
    from agentdock_adapters import get_adapter
    
    # Get adapter for framework
    adapter = get_adapter("langgraph")
    
    # Load agent from entrypoint
    adapter.load("examples.invoice_copilot.app.graph:build_graph")
    
    # Invoke agent
    result = adapter.invoke({
        "document_text": "INVOICE #123...",
        "currency_hint": "USD"
    })
"""

# Protocol and base classes
from .base import (
    AgentAdapter,
    StreamingAgentAdapter,
    AsyncAgentAdapter,
    StatefulAgentAdapter,
)

# Concrete adapter implementations
from .langgraph_adapter import LangGraphAdapter

# Factory and registry functions
from .registry import (
    get_adapter,
    register_adapter,
    list_supported_frameworks,
    is_framework_supported,
    get_adapter_info,
)

# Error classes
from .errors import (
    AdapterError,
    AdapterLoadError,
    ModuleNotFoundError,
    CallableNotFoundError,
    InvalidAgentError,
    AdapterNotLoadedError,
    AgentExecutionError,
    AgentCrashedError,
    InvalidOutputError,
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
    # Factory
    "get_adapter",
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

