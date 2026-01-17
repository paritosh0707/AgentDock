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
from typing import Any, AsyncIterator, Callable, Dict, Optional

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
from .serialization import serialize_for_json

logger = get_logger("langgraph-adapter")


# =============================================================================
# LangGraph Stream Output Handlers
# =============================================================================
# These helper functions process different stream output formats from LangGraph.
# LangGraph's .stream() method returns different formats based on stream_mode:
#
# 1. No stream_mode (default): {node_name: output_dict}
# 2. stream_mode=["updates"]: ("updates", {node_name: output_dict})
# 3. stream_mode=["messages"]: ("messages", message_chunk or (message, metadata))
# 4. stream_mode=["values"]: ("values", full_state_dict)
# 5. Multiple modes: tuples for each mode
# =============================================================================


def _process_langgraph_stream_tuple(
    mode: str,
    data: Any,
    result_queue: Any,
    stream_context: Any,
    emit_steps: bool,
    emit_tokens: bool,
    logger: Any,
    events_filter: Any = None,
) -> None:
    """
    Process a (mode, data) tuple from LangGraph multi-mode streaming.

    Args:
        mode: The stream mode ("messages", "updates", "values", "custom", etc.)
        data: The data associated with this mode
        result_queue: Queue to put processed events
        stream_context: Optional StreamContext for emitting events
        emit_steps: Whether step events should be emitted
        emit_tokens: Whether token events should be emitted
        logger: Logger instance
        events_filter: Optional filter for native custom events
    """
    if mode == "messages":
        # Token streaming from LLM - handle various message formats
        _process_messages_stream(data, result_queue, stream_context, emit_tokens, logger)

    elif mode == "updates":
        # Node updates: {node_name: output_dict}
        _process_updates_stream(data, result_queue, stream_context, emit_steps, logger)

    elif mode == "values":
        # Full state values - emit as checkpoint/state event
        _process_values_stream(data, result_queue, logger)

    elif mode == "custom":
        # Native backend events (progress, checkpoint, user custom)
        _process_native_custom_mode(data, result_queue, events_filter, logger)

    else:
        # Unknown mode - log for debugging
        logger.debug(f"Unknown stream mode: {mode}", data_type=type(data).__name__)


def _process_messages_stream(
    data: Any,
    result_queue: Any,
    stream_context: Any,
    emit_tokens: bool,
    logger: Any,
) -> None:
    """
    Process "messages" stream mode output (token streaming).

    LangGraph messages mode can return:
    - A message object with .content attribute
    - A tuple of (message, metadata)
    - A list of message chunks

    Args:
        data: Message data from LangGraph
        result_queue: Queue to put token events
        stream_context: Optional StreamContext for emitting events
        emit_tokens: Whether tokens should be emitted
        logger: Logger instance
    """
    if not emit_tokens:
        return

    token_content: str | None = None

    # Handle tuple format: (message, metadata)
    if isinstance(data, tuple) and len(data) >= 1:
        msg = data[0]
        if hasattr(msg, "content"):
            content = getattr(msg, "content", None)
            if content:
                token_content = str(content)
        elif isinstance(msg, str):
            token_content = msg
    # Handle string directly
    elif isinstance(data, str):
        token_content = data
    # Handle dict with content key
    elif isinstance(data, dict) and "content" in data:
        content = data["content"]
        if content:
            token_content = str(content)
    # Handle direct message object with content attribute
    elif hasattr(data, "content"):
        content = getattr(data, "content", None)
        if content:
            token_content = str(content)
    # Handle AIMessageChunk or similar with text attribute
    elif hasattr(data, "text"):
        text = getattr(data, "text", None)
        if text:
            token_content = str(text)

    if token_content:
        # Emit through context if available
        if stream_context is not None:
            try:
                stream_context.sync_emit_token(token_content)
            except Exception as e:
                logger.debug(f"Failed to emit token through context: {e}")

        # Put token event in queue
        result_queue.put({
            "type": "token",
            "content": token_content,
        })


def _process_updates_stream(
    data: Any,
    result_queue: Any,
    stream_context: Any,
    emit_steps: bool,
    logger: Any,
) -> None:
    """
    Process "updates" stream mode output (node updates).

    Updates mode returns: {node_name: output_dict}

    Args:
        data: Update data (dict of node outputs)
        result_queue: Queue to put step events
        stream_context: Optional StreamContext for emitting events
        emit_steps: Whether step events should be emitted
        logger: Logger instance
    """
    if not isinstance(data, dict):
        logger.debug("Updates stream data is not a dict", data_type=type(data).__name__)
        return

    for node_name, output in data.items():
        # Emit step event through context if available and steps are allowed
        if stream_context is not None and emit_steps:
            try:
                stream_context.sync_emit_step(
                    node_name=node_name,
                    output_keys=list(output.keys()) if isinstance(output, dict) else [],
                )
            except Exception as e:
                logger.debug(f"Failed to emit step event: {e}")

        # Put step event in queue if allowed
        if emit_steps:
            result_queue.put({
                "type": "step",
                "node": node_name,
                "output": serialize_for_json(output) if isinstance(output, dict) else output,
            })


def _process_values_stream(
    data: Any,
    result_queue: Any,
    logger: Any,
) -> None:
    """
    Process "values" stream mode output (full state).

    Values mode returns the full state dict at each step.
    We emit this as a "state" event type.

    Args:
        data: Full state data
        result_queue: Queue to put state events
        logger: Logger instance
    """
    if isinstance(data, dict):
        result_queue.put({
            "type": "state",
            "data": serialize_for_json(data),
        })
    else:
        logger.debug("Values stream data is not a dict", data_type=type(data).__name__)


def _process_langgraph_default_stream(
    step_output: Dict[str, Any],
    result_queue: Any,
    stream_context: Any,
    emit_steps: bool,
    logger: Any,
) -> None:
    """
    Process default LangGraph stream output (no stream_mode specified).

    Default streaming returns: {node_name: output_dict}

    Args:
        step_output: Dict mapping node names to outputs
        result_queue: Queue to put events
        stream_context: Optional StreamContext for emitting events
        emit_steps: Whether step events should be emitted
        logger: Logger instance
    """
    for node_name, output in step_output.items():
        # Emit step event through context if available and steps are allowed
        if stream_context is not None and emit_steps:
            try:
                stream_context.sync_emit_step(
                    node_name=node_name,
                    output_keys=list(output.keys()) if isinstance(output, dict) else [],
                )
            except Exception as e:
                logger.debug(f"Failed to emit step event: {e}")

        # Put step event in queue if allowed
        if emit_steps:
            result_queue.put({
                "type": "step",
                "node": node_name,
                "output": serialize_for_json(output) if isinstance(output, dict) else output,
            })


def _drain_user_events(
    stream_context: Any,
    result_queue: Any,
    logger: Any,
) -> None:
    """
    Drain user-emitted custom events from StreamContext queue.

    Args:
        stream_context: StreamContext that may have queued events
        result_queue: Queue to put custom events
        logger: Logger instance
    """
    if stream_context is None:
        return

    if not hasattr(stream_context, "drain_queued_events"):
        return

    try:
        user_events = stream_context.drain_queued_events()
        for event in user_events:
            result_queue.put({
                "type": "custom",
                "event_type": getattr(event, "type", "custom"),
                "data": event.model_dump() if hasattr(event, "model_dump") else {},
            })
    except Exception as e:
        logger.debug(f"Failed to drain user events: {e}")


# =============================================================================
# Native Event Handlers (for LangGraph "custom" mode)
# =============================================================================
# When using native LangGraph backend (LangGraphBackend), events emitted via
# StreamContext appear in the stream as ("custom", (event_type, event_data)).
# These handlers process those native events into the standard output format.


def _process_native_progress(event_data: Dict[str, Any], result_queue: Any) -> None:
    """Process native progress event."""
    result_queue.put({
        "type": "progress",
        "step": event_data.get("step", ""),
        "progress": event_data.get("progress", 0.0),
        "message": event_data.get("message"),
    })


def _process_native_checkpoint(event_data: Dict[str, Any], result_queue: Any) -> None:
    """Process native checkpoint event."""
    result_queue.put({
        "type": "checkpoint",
        "name": event_data.get("name", ""),
        "data": event_data.get("data", {}),
    })


def _process_native_token(event_data: Dict[str, Any], result_queue: Any) -> None:
    """Process native token event (fallback path)."""
    result_queue.put({
        "type": "token",
        "content": event_data.get("content", ""),
    })


def _process_native_step(event_data: Dict[str, Any], result_queue: Any) -> None:
    """Process native step event (fallback path)."""
    result_queue.put({
        "type": "step",
        "node": event_data.get("node_name", event_data.get("node", "")),
        "output": event_data.get("output", {}),
    })


def _process_native_user_custom(
    event_name: str,
    event_data: Dict[str, Any],
    result_queue: Any,
) -> None:
    """Process user-defined custom event from native backend."""
    result_queue.put({
        "type": "custom",
        "event_type": event_name,
        "data": event_data,
    })


# Registry of known native event handlers
_NATIVE_EVENT_HANDLERS: Dict[str, Callable[[Dict[str, Any], Any], None]] = {
    "progress": _process_native_progress,
    "checkpoint": _process_native_checkpoint,
    "token": _process_native_token,
    "step": _process_native_step,
}


def _process_native_custom_mode(
    data: Any,
    result_queue: Any,
    events_filter: Any,
    logger: Any,
) -> None:
    """
    Process LangGraph "custom" mode output from native backend.

    Native backend emits: (event_type, event_data)
    - Known events: ("progress", {...}), ("checkpoint", {...})
    - User custom: ("custom:fraud_check", {...})

    Args:
        data: The data from ("custom", data) tuple
        result_queue: Queue to put processed events
        events_filter: Filter to check if event is allowed
        logger: Logger instance
    """
    # Validate format: expect (event_type, event_data)
    if not isinstance(data, tuple) or len(data) != 2:
        logger.debug(f"Invalid native custom event format: {type(data).__name__}")
        return

    event_type, event_data = data

    # Ensure event_data is a dict
    if not isinstance(event_data, dict):
        event_data = {"value": event_data}

    # Check if event is allowed
    if events_filter is not None:
        if event_type.startswith("custom:"):
            custom_name = event_type[7:]
            if not events_filter.is_allowed("custom", custom_name):
                return
        elif not events_filter.is_allowed(event_type):
            return

    # Route to appropriate handler
    if event_type in _NATIVE_EVENT_HANDLERS:
        _NATIVE_EVENT_HANDLERS[event_type](event_data, result_queue)
    elif event_type.startswith("custom:"):
        custom_name = event_type[7:]
        _process_native_user_custom(custom_name, event_data, result_queue)
    else:
        # Unknown type - treat as generic custom
        _process_native_user_custom(event_type, event_data, result_queue)


# =============================================================================
# LangGraph Adapter Class
# =============================================================================


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
            ) from e

        # Step 2: Import module
        try:
            logger.debug("Importing module", module=module_path)
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.error("Module import failed", module=module_path, error=str(e))
            raise ModuleNotFoundError(
                module_path=module_path,
                hint=f"Ensure module is in Python path. Original error: {e}",
            ) from e
        except Exception as e:
            logger.error("Unexpected error importing module", module=module_path, error=str(e))
            raise AdapterLoadError(
                f"Failed to import module '{module_path}': {type(e).__name__}: {e}"
            ) from e

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
            ) from e

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
        self,
        payload: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Any] = None,
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
            context: Optional StreamContext for emitting events

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

            >>> # With StreamContext
            >>> result = adapter.invoke(payload, context=stream_context)
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

        # Set thread-local context if provided
        if context is not None:
            try:
                from dockrion_events import set_current_context

                set_current_context(context)
            except ImportError:
                pass  # Events package not installed

        # Step 3: Log invocation start
        logger.debug(
            "LangGraph agent invocation started",
            entrypoint=self._entrypoint,
            input_keys=list(payload.keys()) if isinstance(payload, dict) else "non-dict",
            has_config=config is not None,
            config_keys=list(config.keys()) if config else None,
            has_context=context is not None,
        )

        # Step 4: Invoke agent
        try:
            # Add context to config if supported
            invoke_config = config.copy() if config else {}
            if context is not None and self._supports_config:
                invoke_config["stream_context"] = context

            if invoke_config and self._supports_config:
                # Pass config to LangGraph for state management
                result = self._runner.invoke(payload, config=invoke_config)
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
        finally:
            # Step 5: Clear thread-local context (always, even on exception)
            if context is not None:
                try:
                    from dockrion_events import set_current_context

                    set_current_context(None)
                except ImportError:
                    pass

        # Step 6: Validate output is dict
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

        # Step 7: Deep serialize result to ensure JSON-serializable output
        result = serialize_for_json(result)

        # Step 8: Log success
        logger.debug(
            "LangGraph agent invocation completed",
            entrypoint=self._entrypoint,
            output_keys=list(result.keys()),
        )

        # Step 9: Return result
        return result

    async def invoke_stream(
        self,
        payload: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Any] = None,
        events_filter: Optional[Any] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream agent execution, yielding events as they occur.

        Uses LangGraph's .stream() method if available to yield
        intermediate results and step completions.

        This is an async generator to be compatible with FastAPI's
        async for iteration in streaming endpoints.

        Pattern A Support:
        - If events_filter is provided, stream modes are dynamically selected
        - If context is not provided but events_filter is, a queue-mode context
          is created automatically for capturing user-emitted events
        - User events are drained and interleaved with framework events

        Args:
            payload: Input dictionary
            config: Optional LangGraph configuration
            context: Optional StreamContext for emitting events
            events_filter: Optional EventsFilter to control which events are yielded

        Yields:
            Dictionaries containing step results and metadata in Dockrion format:
            - {"type": "step", "node": "...", "output": {...}}
            - {"type": "token", "content": "..."}
            - {"type": "custom", "event_type": "...", ...}  # User-emitted events

        Example:
            >>> from dockrion_events import EventsFilter
            >>> filter = EventsFilter(["token", "step"])
            >>> async for event in adapter.invoke_stream(payload, events_filter=filter):
            ...     print(f"Event: {event.get('type')}")
        """
        import asyncio
        import queue as queue_module
        import threading
        import uuid as uuid_module

        # Check adapter is loaded
        if self._runner is None:
            logger.error("invoke_stream called before load")
            raise AdapterNotLoadedError()

        # Check streaming support
        if not self._supports_streaming:
            logger.warning(
                "Agent doesn't support streaming, falling back to invoke",
                entrypoint=self._entrypoint,
            )
            result = self.invoke(payload, config=config, context=context)
            yield {"type": "result", "data": result}
            return

        # Create queue-mode context if not provided but filter is available
        # This enables user code to emit events even in Pattern A
        stream_context = context
        owns_context = False
        if stream_context is None and events_filter is not None:
            try:
                from dockrion_events import LangGraphBackend, StreamContext

                run_id = str(uuid_module.uuid4())

                # Create native LangGraph backend for direct streaming
                streaming_backend = LangGraphBackend()

                stream_context = StreamContext(
                    run_id=run_id,
                    queue_mode=True,
                    events_filter=events_filter,
                    streaming_backend=streaming_backend,
                )
                owns_context = True
                logger.debug(
                    "Created queue-mode context for Pattern A with native backend",
                    run_id=run_id,
                    backend=streaming_backend.name,
                )
            except ImportError:
                pass

        # Set thread-local context if available
        if stream_context is not None:
            try:
                from dockrion_events import set_current_context

                set_current_context(stream_context)
            except ImportError:
                pass

        # Determine which LangGraph stream modes to use based on filter
        stream_modes = None
        if events_filter is not None and hasattr(events_filter, "get_langgraph_stream_modes"):
            stream_modes = events_filter.get_langgraph_stream_modes()
            logger.debug(
                "Using filtered stream modes",
                modes=stream_modes,
            )

        logger.debug(
            "LangGraph streaming started",
            entrypoint=self._entrypoint,
            input_keys=list(payload.keys()) if isinstance(payload, dict) else "non-dict",
            has_filter=events_filter is not None,
            stream_modes=stream_modes,
        )

        # Use a queue to bridge sync stream to async iteration
        result_queue: queue_module.Queue[Dict[str, Any] | None | Exception] = queue_module.Queue()

        def stream_worker() -> None:
            """Worker thread that reads from sync stream and puts to queue."""
            # IMPORTANT: Set thread-local context at the START of the worker thread
            # Thread-local storage doesn't propagate from parent thread, so we must
            # explicitly set it here for get_current_context() to work in graph nodes
            if stream_context is not None:
                try:
                    from dockrion_events import set_current_context

                    set_current_context(stream_context)
                except ImportError:
                    pass

            try:
                # Build config
                stream_config = config.copy() if config else {}
                if stream_context is not None:
                    stream_config["stream_context"] = stream_context

                # Determine if step events should be emitted
                emit_steps = True
                if events_filter is not None:
                    emit_steps = events_filter.is_allowed("step")

                # Build stream() kwargs - pass stream_mode if filter provided modes
                stream_kwargs: Dict[str, Any] = {"config": stream_config}
                if stream_modes is not None:
                    # LangGraph accepts stream_mode as a list or single value
                    stream_kwargs["stream_mode"] = stream_modes

                # Determine if tokens should be emitted
                emit_tokens = True
                if events_filter is not None:
                    emit_tokens = events_filter.is_allowed("token")

                # Stream through the graph
                for step_output in self._runner.stream(payload, **stream_kwargs):  # type: ignore[union-attr]
                    # LangGraph returns different formats based on stream_mode:
                    # - No stream_mode: {node_name: output_dict}
                    # - With stream_mode: (mode, data) tuples

                    if stream_modes is not None and isinstance(step_output, tuple) and len(step_output) == 2:
                        # Multi-mode streaming: (mode, data) tuples
                        mode, data = step_output
                        _process_langgraph_stream_tuple(
                            mode=mode,
                            data=data,
                            result_queue=result_queue,
                            stream_context=stream_context,
                            emit_steps=emit_steps,
                            emit_tokens=emit_tokens,
                            logger=logger,
                            events_filter=events_filter,
                        )
                    elif isinstance(step_output, dict):
                        # Default streaming (no stream_mode): {node_name: output_dict}
                        _process_langgraph_default_stream(
                            step_output=step_output,
                            result_queue=result_queue,
                            stream_context=stream_context,
                            emit_steps=emit_steps,
                            logger=logger,
                        )
                    else:
                        # Unknown format - log and skip
                        logger.debug(
                            "Unknown stream output format",
                            output_type=type(step_output).__name__,
                        )

                    # Drain any user-emitted events from context queue after each step
                    _drain_user_events(stream_context, result_queue, logger)

                # Signal completion
                result_queue.put(None)

            except Exception as e:
                result_queue.put(e)
            finally:
                # Clear thread-local context in worker thread
                if stream_context is not None:
                    try:
                        from dockrion_events import set_current_context

                        set_current_context(None)
                    except ImportError:
                        pass

        # Start worker thread
        worker = threading.Thread(target=stream_worker, daemon=True)
        worker.start()

        try:
            # Async iteration over queue results
            while True:
                # Non-blocking check with async sleep to yield control
                while result_queue.empty():
                    await asyncio.sleep(0.01)  # 10ms poll interval

                item = result_queue.get_nowait()

                if item is None:
                    # Drain any remaining user events before completing
                    if stream_context is not None and hasattr(stream_context, "drain_queued_events"):
                        try:
                            remaining_events = stream_context.drain_queued_events()
                            for event in remaining_events:
                                yield {
                                    "type": "custom",
                                    "event_type": getattr(event, "type", "custom"),
                                    "data": event.model_dump() if hasattr(event, "model_dump") else {},
                                }
                        except Exception as e:
                            logger.debug(f"Failed to drain final user events: {e}")

                    # Stream completed
                    logger.debug(
                        "LangGraph streaming completed",
                        entrypoint=self._entrypoint,
                    )
                    break
                elif isinstance(item, Exception):
                    # Stream errored
                    logger.error(
                        "LangGraph streaming failed",
                        error=str(item),
                        error_type=type(item).__name__,
                        entrypoint=self._entrypoint,
                    )
                    raise AgentExecutionError(
                        f"LangGraph streaming failed: {type(item).__name__}: {item}"
                    ) from item
                else:
                    yield item

        finally:
            # Wait for worker to finish
            worker.join(timeout=1.0)

            # Clear context in main thread as well
            if stream_context is not None:
                try:
                    from dockrion_events import set_current_context

                    set_current_context(None)
                except ImportError:
                    pass

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
