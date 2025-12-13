"""
Adapter Registry and Factory

This module provides factory functions for getting framework-specific adapters
and handler adapters. Uses a registry pattern to map framework names to adapter classes.

Supports two modes:
1. Framework Adapters: For LangGraph, LangChain, etc. (entrypoint mode)
2. Handler Adapter: For direct callable functions (handler mode)

Design:
- Central registry of framework -> adapter mappings
- Factory functions for both modes
- Extensible - easy to add new frameworks
- Type-safe with Protocol

Usage:
    from dockrion_adapters import get_adapter, get_handler_adapter
    
    # Framework mode
    adapter = get_adapter("langgraph")
    adapter.load("app.graph:build_graph")
    result = adapter.invoke(payload)
    
    # Handler mode
    adapter = get_handler_adapter()
    adapter.load("app.service:process_request")
    result = adapter.invoke(payload)
"""

from typing import Dict, Type
from dockrion_common import ValidationError, get_logger

from .base import AgentAdapter
from .langgraph_adapter import LangGraphAdapter
from .handler_adapter import HandlerAdapter

logger = get_logger("adapter-registry")

# Registry mapping framework names to adapter classes
_ADAPTER_REGISTRY: Dict[str, Type[AgentAdapter]] = {
    "langgraph": LangGraphAdapter,
    "custom": HandlerAdapter,  # Handler mode uses "custom" framework
    # Phase 2: Add more frameworks
    # "langchain": LangChainAdapter,
    # "crewai": CrewAIAdapter,
    # "autogen": AutoGenAdapter,
}


def get_adapter(framework: str) -> AgentAdapter:
    """
    Get adapter instance for framework.
    
    Factory function that returns the appropriate adapter for the
    specified framework. Validates framework is supported.
    
    Args:
        framework: Framework name (e.g., "langgraph", "langchain")
                  Must be one of the registered frameworks
        
    Returns:
        Fresh adapter instance for the framework
        
    Raises:
        ValidationError: If framework is not supported
        
    Examples:
        >>> # Get LangGraph adapter
        >>> adapter = get_adapter("langgraph")
        >>> adapter.load("app.graph:build_graph")
        
        >>> # Error if unsupported
        >>> adapter = get_adapter("unsupported")
        ValidationError: Unsupported framework: 'unsupported'
    """
    framework_lower = framework.lower().strip()
    
    if framework_lower not in _ADAPTER_REGISTRY:
        supported = ", ".join(sorted(_ADAPTER_REGISTRY.keys()))
        logger.error(
            "Unsupported framework requested",
            framework=framework,
            supported_frameworks=supported
        )
        raise ValidationError(
            f"Unsupported framework: '{framework}'. "
            f"Supported frameworks: {supported}"
        )
    
    adapter_class = _ADAPTER_REGISTRY[framework_lower]
    adapter = adapter_class()
    
    logger.debug("Adapter created", framework=framework_lower)
    
    return adapter


def get_handler_adapter() -> HandlerAdapter:
    """
    Get a HandlerAdapter instance for direct callable functions.
    
    Use this when the agent config specifies a `handler` instead of `entrypoint`.
    Handler mode is for service wrapper functions that process requests directly
    without going through a framework-specific agent object.
    
    Returns:
        Fresh HandlerAdapter instance
        
    Examples:
        >>> adapter = get_handler_adapter()
        >>> adapter.load("app.service:process_request")
        >>> result = adapter.invoke({"query": "hello"})
        
    See Also:
        get_adapter: For framework-specific agents (entrypoint mode)
    """
    adapter = HandlerAdapter()
    logger.debug("Handler adapter created")
    return adapter


def register_adapter(framework: str, adapter_class: Type[AgentAdapter]) -> None:
    """
    Register custom adapter for a framework.
    
    Allows users to add custom framework adapters at runtime.
    Useful for:
    - Custom internal frameworks
    - Testing with mock adapters
    - Extending dockrion with new frameworks
    
    Args:
        framework: Framework name (will be lowercased)
        adapter_class: Adapter class implementing AgentAdapter protocol
        
    Examples:
        >>> class MyCustomAdapter:
        ...     def load(self, entrypoint): ...
        ...     def invoke(self, payload): ...
        ...     def get_metadata(self): ...
        
        >>> register_adapter("custom", MyCustomAdapter)
        >>> adapter = get_adapter("custom")
    """
    framework_lower = framework.lower().strip()
    
    # Validate adapter implements protocol (basic check)
    required_methods = ['load', 'invoke', 'get_metadata']
    for method in required_methods:
        if not hasattr(adapter_class, method):
            raise ValueError(
                f"Adapter class must implement {method}() method. "
                f"Got: {adapter_class.__name__}"
            )
    
    _ADAPTER_REGISTRY[framework_lower] = adapter_class
    
    logger.info(
        "Custom adapter registered",
        framework=framework_lower,
        adapter_class=adapter_class.__name__
    )


def list_supported_frameworks() -> list[str]:
    """
    Get list of supported frameworks.
    
    Returns:
        List of framework names that have adapters
        
    Examples:
        >>> frameworks = list_supported_frameworks()
        >>> print(frameworks)
        ['langgraph']
    """
    return sorted(_ADAPTER_REGISTRY.keys())


def is_framework_supported(framework: str) -> bool:
    """
    Check if framework is supported.
    
    Args:
        framework: Framework name to check
        
    Returns:
        True if supported, False otherwise
        
    Examples:
        >>> is_framework_supported("langgraph")
        True
        >>> is_framework_supported("unsupported")
        False
    """
    return framework.lower().strip() in _ADAPTER_REGISTRY


def get_adapter_info(framework: str) -> Dict[str, any]:
    """
    Get information about an adapter without instantiating it.
    
    Args:
        framework: Framework name
        
    Returns:
        Dictionary with adapter information
        
    Raises:
        ValidationError: If framework not supported
        
    Examples:
        >>> info = get_adapter_info("langgraph")
        >>> print(info)
        {
            'framework': 'langgraph',
            'adapter_class': 'LangGraphAdapter',
            'supported': True
        }
    """
    framework_lower = framework.lower().strip()
    
    if framework_lower not in _ADAPTER_REGISTRY:
        supported = ", ".join(sorted(_ADAPTER_REGISTRY.keys()))
        raise ValidationError(
            f"Unsupported framework: '{framework}'. "
            f"Supported frameworks: {supported}"
        )
    
    adapter_class = _ADAPTER_REGISTRY[framework_lower]
    
    return {
        "framework": framework_lower,
        "adapter_class": adapter_class.__name__,
        "supported": True,
        "module": adapter_class.__module__,
    }
