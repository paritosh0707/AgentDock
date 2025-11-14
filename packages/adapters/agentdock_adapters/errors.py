"""
AgentDock Adapter Error Classes

This module defines the error hierarchy for adapter-related failures.
All errors inherit from AgentDockError (from common package) for consistent handling.

Error Hierarchy:
    AgentDockError (from common)
    └── AdapterError
        ├── AdapterLoadError
        │   ├── ModuleNotFoundError
        │   ├── CallableNotFoundError
        │   └── InvalidAgentError
        ├── AdapterNotLoadedError
        └── AgentExecutionError
            ├── AgentCrashedError
            └── InvalidOutputError

Usage:
    from agentdock_adapters.errors import AdapterLoadError
    
    raise AdapterLoadError("Failed to import module 'app.graph'")
"""

from agentdock_common import AgentDockError


class AdapterError(AgentDockError):
    """
    Base exception for all adapter-related errors.
    
    All adapter errors inherit from this class for easy catching
    and consistent error handling.
    """
    
    def __init__(self, message: str):
        super().__init__(message, code="ADAPTER_ERROR")


class AdapterLoadError(AdapterError):
    """
    Raised when agent loading fails.
    
    Common causes:
    - Module not found (import error)
    - Callable doesn't exist in module
    - Factory function crashes
    - Agent missing required methods
    
    Examples:
        >>> raise AdapterLoadError(
        ...     "Failed to import module 'app.graph': No module named 'app'"
        ... )
    """
    
    def __init__(self, message: str):
        super().__init__(message)
        self.code = "ADAPTER_LOAD_ERROR"


class ModuleNotFoundError(AdapterLoadError):
    """
    Raised when module cannot be imported.
    
    Examples:
        >>> raise ModuleNotFoundError(
        ...     "Module 'app.graph' not found. "
        ...     "Hint: Ensure module is in Python path"
        ... )
    """
    
    def __init__(self, module_path: str, hint: str = None):
        message = f"Module '{module_path}' not found"
        if hint:
            message += f". Hint: {hint}"
        else:
            message += ". Hint: Ensure module is in Python path"
        super().__init__(message)
        self.code = "MODULE_NOT_FOUND"
        self.module_path = module_path


class CallableNotFoundError(AdapterLoadError):
    """
    Raised when callable doesn't exist in module.
    
    Examples:
        >>> raise CallableNotFoundError(
        ...     "Module 'app.graph' has no function 'build_graph'. "
        ...     "Available: ['helper', 'utils']"
        ... )
    """
    
    def __init__(self, module_path: str, callable_name: str, available: list = None):
        message = f"Module '{module_path}' has no function '{callable_name}'"
        if available:
            message += f". Available: {available}"
        else:
            message += ". Hint: Check function name in entrypoint"
        super().__init__(message)
        self.code = "CALLABLE_NOT_FOUND"
        self.module_path = module_path
        self.callable_name = callable_name


class InvalidAgentError(AdapterLoadError):
    """
    Raised when loaded agent doesn't meet requirements.
    
    Common causes:
    - Agent missing .invoke() method
    - Agent returns wrong type from factory
    - Agent interface incompatible with framework
    
    Examples:
        >>> raise InvalidAgentError(
        ...     "Agent must have .invoke() method. Got type: MyAgent. "
        ...     "Hint: Ensure your factory returns compiled graph"
        ... )
    """
    
    def __init__(self, message: str):
        super().__init__(message)
        self.code = "INVALID_AGENT"


class AdapterNotLoadedError(AdapterError):
    """
    Raised when invoke() called before load().
    
    Examples:
        >>> raise AdapterNotLoadedError(
        ...     "Adapter not loaded. Call .load(entrypoint) before .invoke()"
        ... )
    """
    
    def __init__(self, message: str = None):
        if not message:
            message = "Adapter not loaded. Call .load(entrypoint) before .invoke()"
        super().__init__(message)
        self.code = "ADAPTER_NOT_LOADED"


class AgentExecutionError(AdapterError):
    """
    Raised when agent invocation fails.
    
    This is a catch-all for errors during agent execution.
    The original exception is preserved in the exception chain.
    
    Examples:
        >>> try:
        ...     result = agent.invoke(payload)
        ... except Exception as e:
        ...     raise AgentExecutionError(
        ...         f"Agent invocation failed: {type(e).__name__}: {e}"
        ...     ) from e
    """
    
    def __init__(self, message: str):
        super().__init__(message)
        self.code = "AGENT_EXECUTION_ERROR"


class AgentCrashedError(AgentExecutionError):
    """
    Raised when agent crashes during execution.
    
    Examples:
        >>> raise AgentCrashedError(
        ...     "Agent crashed with error: ZeroDivisionError"
        ... )
    """
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.code = "AGENT_CRASHED"
        self.original_error = original_error


class InvalidOutputError(AgentExecutionError):
    """
    Raised when agent returns invalid output.
    
    Common causes:
    - Agent returns non-dict type
    - Output missing required fields
    - Output has wrong structure
    
    Examples:
        >>> raise InvalidOutputError(
        ...     "Agent must return dict, got list. "
        ...     "Hint: Ensure .invoke() returns dict"
        ... )
    """
    
    def __init__(self, message: str, actual_type: type = None):
        super().__init__(message)
        self.code = "INVALID_OUTPUT"
        self.actual_type = actual_type

