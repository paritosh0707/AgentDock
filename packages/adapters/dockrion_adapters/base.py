"""
dockrion Adapter Protocol

This module defines the AgentAdapter protocol that all framework adapters must implement.
Using Protocol (PEP 544) provides structural subtyping without requiring inheritance.

Design:
- Protocol-based for flexibility (no forced inheritance)
- Simple interface: load, invoke, get_metadata
- Framework-agnostic (works for any agent framework)

Usage:
    from dockrion_adapters.base import AgentAdapter
    
    class MyFrameworkAdapter(AgentAdapter):
        def load(self, entrypoint: str) -> None:
            # Implementation
            pass
        
        def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            # Implementation
            pass
        
        def get_metadata(self) -> Dict[str, Any]:
            # Implementation
            pass
"""

from typing import Protocol, Dict, Any, Optional, Iterator


class AgentAdapter(Protocol):
    """
    Protocol defining the interface for all agent framework adapters.
    
    All adapter implementations must provide these methods to ensure
    uniform interaction regardless of the underlying framework.
    
    Attributes:
        _runner: The loaded agent instance (framework-specific)
        _entrypoint: The entrypoint string used to load the agent
        
    Methods:
        load: Load agent from entrypoint
        invoke: Invoke agent with input payload
        get_metadata: Get adapter information
    """
    
    def load(self, entrypoint: str) -> None:
        """
        Load agent from entrypoint.
        
        The entrypoint format is "module.path:callable" where:
        - module.path: Python module path (e.g., "app.graph")
        - callable: Factory function name (e.g., "build_graph")
        
        The factory function must return an object with .invoke() method.
        
        Args:
            entrypoint: Entrypoint string in format "module.path:callable"
            
        Raises:
            AdapterLoadError: If loading fails for any reason
            ModuleNotFoundError: If module cannot be imported
            CallableNotFoundError: If callable doesn't exist in module
            InvalidAgentError: If agent doesn't have required interface
            
        Examples:
            >>> adapter = LangGraphAdapter()
            >>> adapter.load("examples.invoice_copilot.app.graph:build_graph")
            # Agent loaded and ready for invocations
        """
        ...
    
    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke agent with input payload.
        
        The payload and return value are both dictionaries, allowing
        flexible schema definitions via Dockfile's io_schema.
        
        Args:
            payload: Input dictionary (structure defined by io_schema.input)
            
        Returns:
            Output dictionary (structure defined by io_schema.output)
            
        Raises:
            AdapterNotLoadedError: If load() hasn't been called
            AgentExecutionError: If agent invocation fails
            InvalidOutputError: If agent returns non-dict type
            
        Examples:
            >>> result = adapter.invoke({
            ...     "document_text": "INVOICE #123...",
            ...     "currency_hint": "USD"
            ... })
            >>> print(result)
            {'vendor': 'Acme Corp', 'invoice_number': 'INV-123', ...}
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get adapter metadata for introspection.
        
        Returns metadata about the adapter and loaded agent for:
        - Health checks
        - Debugging
        - Telemetry
        - API introspection
        
        Returns:
            Dictionary with adapter information including:
                - framework: Framework name (e.g., "langgraph")
                - adapter_version: Adapter version
                - loaded: Whether agent is loaded
                - agent_type: Type of loaded agent (if loaded)
                - entrypoint: Entrypoint used to load agent
                - supports_streaming: Whether adapter supports streaming
                - supports_async: Whether adapter supports async
                
        Examples:
            >>> metadata = adapter.get_metadata()
            >>> print(metadata)
            {
                'framework': 'langgraph',
                'adapter_version': '0.1.0',
                'loaded': True,
                'agent_type': 'CompiledGraph',
                'entrypoint': 'app.graph:build_graph',
                'supports_streaming': False,
                'supports_async': False
            }
        """
        ...


class StreamingAgentAdapter(AgentAdapter, Protocol):
    """
    Extended protocol for adapters that support streaming.
    
    Phase 2 feature - not required for MVP.
    Allows streaming agent responses for long-running tasks.
    """
    
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
        ...


class AsyncAgentAdapter(AgentAdapter, Protocol):
    """
    Extended protocol for adapters that support async invocation.
    
    Phase 2 feature - not required for MVP.
    Allows non-blocking agent invocations.
    """
    
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
        ...


class StatefulAgentAdapter(AgentAdapter, Protocol):
    """
    Extended protocol for adapters that support stateful execution.
    
    Phase 2 feature - not required for MVP.
    Allows multi-turn conversations with memory.
    """
    
    def invoke(
        self, 
        payload: Dict[str, Any], 
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke with optional configuration for state management.
        
        Args:
            payload: Input dictionary
            config: Optional configuration including:
                - thread_id: Conversation thread identifier
                - checkpoint_id: State checkpoint to resume from
                - recursion_limit: Max iterations (framework-specific)
                
        Returns:
            Output dictionary
            
        Examples:
            >>> # Start conversation
            >>> result = adapter.invoke(
            ...     {"query": "Hello"},
            ...     config={"thread_id": "conv-123"}
            ... )
            >>> # Continue conversation (has memory)
            >>> result = adapter.invoke(
            ...     {"query": "What did I say?"},
            ...     config={"thread_id": "conv-123"}
            ... )
        """
        ...
