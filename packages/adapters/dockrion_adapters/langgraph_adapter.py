"""
LangGraph Adapter Implementation

This module provides the adapter for LangGraph compiled graphs.
Enables dockrion to invoke LangGraph agents through a uniform interface.

LangGraph Overview:
- Framework for building stateful, multi-step agent workflows
- Uses graph-based execution model (nodes = steps, edges = transitions)
- Compiled graphs have .invoke(dict) -> dict interface

Usage:
    from dockrion_adapters import LangGraphAdapter

    adapter = LangGraphAdapter()
    adapter.load("examples.invoice_copilot.app.graph:build_graph")
    result = adapter.invoke({"document_text": "INVOICE #123..."})
"""

import importlib
import inspect
from typing import Any, Dict, Optional

from dockrion_common import get_logger, validate_entrypoint

from .errors import (
    AdapterLoadError,
    AdapterNotLoadedError,
    AgentExecutionError,
    CallableNotFoundError,
    InvalidAgentError,
    InvalidOutputError,
    ModuleNotFoundError,
)

logger = get_logger("langgraph-adapter")


class LangGraphAdapter:
    """
    Adapter for LangGraph compiled graphs.

    Provides uniform interface to LangGraph agents, handling:
    - Dynamic loading from entrypoint
    - Invocation with dict input/output (with optional config)
    - Error normalization
    - Metadata extraction
    - Optional strict type validation

    Supports two validation modes:
    - Duck typing (default): Checks for .invoke() method presence
    - Strict typing (optional): Validates actual LangGraph types (requires langgraph installed)

    Attributes:
        _runner: Loaded LangGraph compiled app (has .invoke() method)
        _entrypoint: Entrypoint string used to load agent
        _strict_validation: Whether to perform strict LangGraph type checking
        _supports_streaming: Whether agent supports streaming (Phase 2)
        _supports_async: Whether agent supports async (Phase 2)
        _supports_config: Whether agent's invoke() accepts config parameter

    Examples:
        >>> # Basic usage with duck typing (default)
        >>> adapter = LangGraphAdapter()
        >>> adapter.load("app.graph:build_graph")
        >>> result = adapter.invoke({"input": "test"})

        >>> # With strict validation
        >>> adapter = LangGraphAdapter(strict_validation=True)
        >>> adapter.load("app.graph:build_graph")

        >>> # With config for state persistence
        >>> result = adapter.invoke(
        ...     {"query": "Hello"},
        ...     config={"thread_id": "user-123"}
        ... )
    """

    def __init__(self, strict_validation: bool = False):
        """
        Initialize adapter with optional strict validation.

        Args:
            strict_validation: If True, validates that loaded agent is an actual
                             LangGraph compiled graph type (Pregel/CompiledStateGraph).
                             Requires langgraph package to be installed.
                             Default: False (uses duck typing - checks for .invoke() only)

        Examples:
            >>> # Default: Duck typing (lenient, no langgraph dependency)
            >>> adapter = LangGraphAdapter()

            >>> # Strict: Type checking (requires langgraph installed)
            >>> adapter = LangGraphAdapter(strict_validation=True)
        """
        self._runner: Optional[Any] = None
        self._entrypoint: Optional[str] = None
        self._strict_validation: bool = strict_validation
        self._supports_streaming: bool = False
        self._supports_async: bool = False
        self._supports_config: bool = False

        logger.debug("LangGraphAdapter initialized", strict_validation=strict_validation)

    def _validate_langgraph_type(self) -> bool:
        """
        Strict validation: Check if agent is actual LangGraph compiled graph.

        Uses lazy imports to avoid requiring langgraph as a dependency.
        Only called when strict_validation=True.

        Returns:
            True if validation passed or was skipped
            False if langgraph not installed (falls back to duck typing)

        Raises:
            InvalidAgentError: If strict validation enabled and agent is wrong type

        Examples:
            >>> adapter = LangGraphAdapter(strict_validation=True)
            >>> adapter.load("app.graph:build_graph")
            # Validates agent is Pregel or CompiledStateGraph
        """
        if not self._strict_validation:
            return False  # Skip strict validation

        try:
            # Lazy import - only when strict validation requested
            from langgraph.pregel import Pregel

            # Try to import CompiledStateGraph (newer LangGraph versions)
            valid_types: tuple[type, ...]
            try:
                from langgraph.graph.state import CompiledStateGraph

                valid_types = (Pregel, CompiledStateGraph)
            except ImportError:
                # Older versions might not have CompiledStateGraph
                valid_types = (Pregel,)

            if not isinstance(self._runner, valid_types):
                agent_type = type(self._runner).__name__
                agent_module = type(self._runner).__module__
                expected_types = [t.__name__ for t in valid_types]

                logger.error(
                    "Strict validation failed: Invalid LangGraph type",
                    agent_type=agent_type,
                    agent_module=agent_module,
                    expected_types=expected_types,
                )

                raise InvalidAgentError(
                    f"Strict validation failed: Agent is not a LangGraph compiled graph. "
                    f"Expected types: {expected_types}, "
                    f"Got: {agent_type} from module '{agent_module}'. "
                    f"Hint: Ensure your factory returns graph.compile(). "
                    f"If using a custom agent, disable strict_validation."
                )

            logger.debug(
                "Strict validation passed",
                agent_type=type(self._runner).__name__,
                valid_types=[t.__name__ for t in valid_types],
            )
            return True

        except ImportError as e:
            logger.warning(
                "Strict validation requested but LangGraph not installed. "
                "Falling back to duck typing validation. "
                "Install langgraph for strict type checking: pip install langgraph",
                error=str(e),
            )
            return False

    def _validate_invoke_signature(self) -> bool:
        """
        Validate invoke() method signature and detect config support.

        Checks if agent's invoke() method accepts:
        1. At least one parameter (input dict)
        2. Optional second parameter (config dict)

        Updates self._supports_config based on signature.

        Returns:
            True if signature is valid, False if inspection failed

        Raises:
            InvalidAgentError: If invoke() signature is invalid
        """
        assert self._runner is not None, "Cannot validate signature before loading agent"
        invoke_method = self._runner.invoke

        try:
            sig = inspect.signature(invoke_method)
            params = list(sig.parameters.keys())

            # Remove 'self' if present (bound method)
            if params and params[0] == "self":
                params = params[1:]

            # Should have at least 1 parameter (input)
            if len(params) < 1:
                logger.error("Invalid invoke() signature: No parameters", signature=str(sig))
                raise InvalidAgentError(
                    f"Agent .invoke() must accept at least 1 parameter (input dict). "
                    f"Got signature: {sig}. "
                    f"Hint: Check your agent's invoke() method definition."
                )

            # Check if config parameter is supported
            # LangGraph typically has: invoke(input, config=None, **kwargs)
            self._supports_config = len(params) >= 2 or any(
                param.kind == inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values()
            )

            if self._supports_config:
                logger.debug("Agent supports config parameter", signature=str(sig), params=params)
            else:
                logger.debug(
                    "Agent does not support config parameter", signature=str(sig), params=params
                )

            return True

        except Exception as e:
            logger.warning(
                "Could not inspect invoke() signature. Assuming no config support.", error=str(e)
            )
            # Don't fail - signature inspection is best-effort
            self._supports_config = False
            return False

    def load(self, entrypoint: str) -> None:
        """
        Load LangGraph agent from entrypoint.

        Process:
        1. Validate entrypoint format (module.path:callable)
        2. Import module dynamically
        3. Get factory function
        4. Call factory to get compiled graph
        5. Validate graph has .invoke() method
        6. Store graph for invocations
        7. Check for optional methods (stream, ainvoke)

        Args:
            entrypoint: Format "module.path:callable"
                       Example: "examples.invoice_copilot.app.graph:build_graph"

        Raises:
            AdapterLoadError: If any step fails
            ModuleNotFoundError: If module can't be imported
            CallableNotFoundError: If callable doesn't exist
            InvalidAgentError: If agent missing .invoke()

        Examples:
            >>> adapter = LangGraphAdapter()
            >>> adapter.load("examples.invoice_copilot.app.graph:build_graph")
            # Agent loaded successfully
        """
        logger.info("Loading LangGraph agent", entrypoint=entrypoint)

        # Step 1: Validate and parse entrypoint
        try:
            module_path, callable_name = validate_entrypoint(entrypoint)
        except Exception as e:
            logger.error("Invalid entrypoint format", entrypoint=entrypoint, error=str(e))
            raise AdapterLoadError(
                f"Invalid entrypoint format: {entrypoint}. "
                f"Expected 'module.path:callable'. Error: {e}"
            )

        # Step 2: Import module
        try:
            logger.debug("Importing module", module=module_path)
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.error("Module import failed", module=module_path, error=str(e))
            raise ModuleNotFoundError(
                module_path=module_path,
                hint=f"Ensure module is in Python path. Original error: {e}",
            )
        except Exception as e:
            logger.error("Unexpected error importing module", module=module_path, error=str(e))
            raise AdapterLoadError(
                f"Failed to import module '{module_path}': {type(e).__name__}: {e}"
            )

        # Step 3: Get factory function
        if not hasattr(module, callable_name):
            # Get available functions for helpful error message
            available = [name for name in dir(module) if not name.startswith("_")]
            logger.error(
                "Callable not found in module",
                module=module_path,
                callable=callable_name,
                available=available[:10],  # Limit to first 10
            )
            raise CallableNotFoundError(
                module_path=module_path, callable_name=callable_name, available=available[:10]
            )

        try:
            factory = getattr(module, callable_name)
            logger.debug("Factory function found", callable=callable_name)
        except Exception as e:
            logger.error("Failed to get callable", callable=callable_name, error=str(e))
            raise AdapterLoadError(
                f"Failed to get callable '{callable_name}' from module '{module_path}': {e}"
            )

        # Step 4: Call factory to get agent
        try:
            logger.debug("Calling factory function", factory=callable_name)
            self._runner = factory()
        except Exception as e:
            logger.error("Factory function failed", factory=callable_name, error=str(e))
            raise AdapterLoadError(
                f"Factory function '{callable_name}' failed: {type(e).__name__}: {e}. "
                f"Hint: Check your agent code for errors."
            ) from e

        # Step 5: Validate agent has .invoke() method
        if not hasattr(self._runner, "invoke"):
            agent_type = type(self._runner).__name__
            logger.error("Agent missing invoke method", agent_type=agent_type)
            raise InvalidAgentError(
                f"Agent must have .invoke() method. Got type: {agent_type}. "
                f"Hint: For LangGraph, ensure you return graph.compile(), not the graph itself."
            )

        # Step 6: Check if invoke is callable
        if not callable(self._runner.invoke):
            agent_type = type(self._runner).__name__
            logger.error("Agent invoke is not callable", agent_type=agent_type)
            raise InvalidAgentError(f"Agent .invoke() must be callable. Got type: {agent_type}")

        # Step 7: Validate invoke() signature and detect config support
        self._validate_invoke_signature()

        # Step 8: Perform strict type validation if enabled
        if self._strict_validation:
            self._validate_langgraph_type()
        else:
            # Soft validation - just log warning if not LangGraph type
            agent_module = type(self._runner).__module__
            if not agent_module.startswith("langgraph"):
                logger.warning(
                    "Agent may not be a LangGraph type. "
                    "Enable strict_validation=True for type checking.",
                    agent_type=type(self._runner).__name__,
                    agent_module=agent_module,
                )

        # Step 9: Store entrypoint
        self._entrypoint = entrypoint

        # Step 10: Check for optional methods (Phase 2 features)
        self._supports_streaming = hasattr(self._runner, "stream") and callable(self._runner.stream)
        self._supports_async = hasattr(self._runner, "ainvoke") and callable(self._runner.ainvoke)

        logger.info(
            "✅ LangGraph agent loaded successfully",
            entrypoint=entrypoint,
            agent_type=type(self._runner).__name__,
            agent_module=type(self._runner).__module__,
            strict_validation=self._strict_validation,
            supports_streaming=self._supports_streaming,
            supports_async=self._supports_async,
            supports_config=self._supports_config,
        )

    def invoke(
        self, payload: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke LangGraph agent with input payload and optional config.

        Process:
        1. Check adapter is loaded
        2. Validate config usage
        3. Log invocation start
        4. Call agent's .invoke() method (with or without config)
        5. Validate output is dict
        6. Log invocation complete
        7. Return result

        Args:
            payload: Input dictionary (matches io_schema.input)
            config: Optional LangGraph configuration dict with:
                - thread_id: For conversation state persistence across invocations
                - checkpoint_id: Resume from specific checkpoint
                - recursion_limit: Max graph iterations (default: 25)
                - run_name: For tracing/debugging
                - configurable: Dict of custom config values

        Returns:
            Output dictionary (matches io_schema.output)

        Raises:
            AdapterNotLoadedError: If load() not called
            AgentExecutionError: If agent invocation fails
            InvalidOutputError: If agent returns non-dict

        Examples:
            >>> # Simple invocation
            >>> result = adapter.invoke({
            ...     "document_text": "INVOICE #123...",
            ...     "currency_hint": "USD"
            ... })

            >>> # With state persistence (multi-turn conversation)
            >>> result = adapter.invoke(
            ...     {"query": "What's the weather?"},
            ...     config={"thread_id": "user-123"}
            ... )
            >>> # Next turn remembers context
            >>> result = adapter.invoke(
            ...     {"query": "What about tomorrow?"},
            ...     config={"thread_id": "user-123"}
            ... )

            >>> # With recursion limit
            >>> result = adapter.invoke(
            ...     {"input": "complex task"},
            ...     config={"recursion_limit": 50}
            ... )
        """
        # Step 1: Check adapter is loaded
        if self._runner is None:
            logger.error("Invoke called before load")
            raise AdapterNotLoadedError()

        # Step 2: Validate config usage
        if config and not self._supports_config:
            logger.warning(
                "Config provided but agent's invoke() doesn't support config parameter. "
                "Config will be ignored. This may happen with custom agents or older LangGraph versions.",
                config_keys=list(config.keys()),
                agent_type=type(self._runner).__name__,
            )
            config = None  # Ignore config if not supported

        # Step 3: Log invocation start
        logger.debug(
            "LangGraph agent invocation started",
            entrypoint=self._entrypoint,
            input_keys=list(payload.keys()) if isinstance(payload, dict) else "non-dict",
            has_config=config is not None,
            config_keys=list(config.keys()) if config else None,
        )

        # Step 4: Invoke agent
        try:
            if config and self._supports_config:
                # Pass config to LangGraph for state management
                result = self._runner.invoke(payload, config=config)
            else:
                # Simple invocation without config
                result = self._runner.invoke(payload)
        except TypeError as e:
            # Common error: wrong input format or config format
            logger.error(
                "Agent invocation failed with TypeError",
                error=str(e),
                payload_type=type(payload).__name__,
                has_config=config is not None,
            )
            raise AgentExecutionError(
                f"LangGraph invocation failed with TypeError: {e}. "
                f"Hint: Check that your input matches the agent's expected format. "
                f"If using config, ensure agent supports config parameter."
            ) from e
        except Exception as e:
            # General execution error
            logger.error(
                "Agent invocation failed",
                error=str(e),
                error_type=type(e).__name__,
                entrypoint=self._entrypoint,
                has_config=config is not None,
            )
            raise AgentExecutionError(
                f"LangGraph invocation failed: {type(e).__name__}: {e}"
            ) from e

        # Step 5: Validate output is dict
        if not isinstance(result, dict):
            actual_type = type(result).__name__
            logger.error(
                "Agent returned non-dict output",
                actual_type=actual_type,
                entrypoint=self._entrypoint,
            )
            raise InvalidOutputError(
                f"Agent must return dict, got {actual_type}. "
                f"Hint: Ensure your agent's .invoke() returns a dictionary.",
                actual_type=type(result),
            )

        # Step 5: Log success
        logger.debug(
            "LangGraph agent invocation completed",
            entrypoint=self._entrypoint,
            output_keys=list(result.keys()),
        )

        # Step 6: Return result
        return result

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get adapter metadata for introspection.

        Returns metadata about the adapter and loaded agent:
        - framework: Always "langgraph"
        - adapter_version: Current adapter version
        - loaded: Whether agent is loaded
        - agent_type: Type name of loaded agent
        - agent_module: Module path of agent type
        - entrypoint: Entrypoint string (if loaded)
        - strict_validation: Whether strict type validation was enabled
        - supports_streaming: Whether streaming is available
        - supports_async: Whether async is available
        - supports_config: Whether config parameter is supported
        - is_langgraph_type: Whether agent module is from langgraph

        Returns:
            Metadata dictionary with adapter and agent information

        Examples:
            >>> metadata = adapter.get_metadata()
            >>> print(metadata)
            {
                'framework': 'langgraph',
                'adapter_version': '0.1.0',
                'loaded': True,
                'agent_type': 'Pregel',
                'agent_module': 'langgraph.pregel',
                'entrypoint': 'app.graph:build_graph',
                'strict_validation': False,
                'supports_streaming': True,
                'supports_async': True,
                'supports_config': True,
                'is_langgraph_type': True
            }
        """
        metadata = {
            "framework": "langgraph",
            "adapter_version": "0.1.0",
            "loaded": self._runner is not None,
            "agent_type": type(self._runner).__name__ if self._runner else None,
            "agent_module": type(self._runner).__module__ if self._runner else None,
            "entrypoint": self._entrypoint,
            "strict_validation": self._strict_validation,
            "supports_streaming": self._supports_streaming,
            "supports_async": self._supports_async,
            "supports_config": self._supports_config,
        }

        # Add validation info if loaded
        if self._runner:
            agent_module = type(self._runner).__module__
            metadata["is_langgraph_type"] = agent_module.startswith("langgraph")
        else:
            metadata["is_langgraph_type"] = None

        return metadata

    def health_check(self) -> bool:
        """
        Quick health check for adapter.

        Verifies that:
        - Adapter is loaded
        - Agent is responsive (can handle test invocation)

        Returns:
            True if healthy, False otherwise

        Examples:
            >>> if adapter.health_check():
            ...     print("Adapter ready")
        """
        if not self._runner:
            logger.debug("Health check failed: adapter not loaded")
            return False

        try:
            # Quick test invocation with minimal payload
            # Many LangGraph agents ignore unexpected keys
            test_payload = {"__health_check__": True}
            self._runner.invoke(test_payload)
            logger.debug("Health check passed")
            return True
        except Exception as e:
            logger.debug("Health check failed", error=str(e))
            return False
