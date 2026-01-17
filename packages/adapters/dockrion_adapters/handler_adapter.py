"""
Handler Adapter Implementation

This module provides the adapter for direct callable handler functions.
Enables dockrion to invoke user-defined service functions through a uniform interface.

Handler functions are direct callables that process requests without requiring
a framework-specific agent object. This is useful for:
- Service wrappers that do preprocessing/postprocessing
- Custom business logic that doesn't fit framework patterns
- Simpler use cases that don't need full agent workflows

Handler Contract:
    # Basic handler
    def handler(payload: dict) -> dict:
        '''Process request and return response.'''
        ...

    # Handler with StreamContext
    def handler(payload: dict, context: StreamContext) -> dict:
        '''Process request with streaming support.'''
        context.emit_progress("processing", 0.5)
        ...

Usage:
    from dockrion_adapters import HandlerAdapter

    adapter = HandlerAdapter()
    adapter.load("app.service:process_request")
    result = adapter.invoke({"query": "hello"})

    # With StreamContext
    result = adapter.invoke({"query": "hello"}, context=stream_context)
"""

import asyncio
import importlib
import inspect
from typing import Any, Callable, Dict, Optional

from dockrion_common import get_logger, validate_handler

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

logger = get_logger("handler-adapter")


class HandlerAdapter:
    """
    Adapter for direct callable handler functions.

    Provides uniform interface to user-defined service functions, handling:
    - Dynamic loading from handler path
    - Invocation with dict input/output
    - Support for both sync and async handlers
    - StreamContext injection for streaming support
    - Error normalization
    - Metadata extraction

    Attributes:
        _handler: Loaded callable function
        _handler_path: Handler path string used to load
        _is_async: Whether handler is an async function
        _signature: Handler's call signature
        _accepts_context: Whether handler accepts StreamContext parameter

    Examples:
        >>> adapter = HandlerAdapter()
        >>> adapter.load("app.service:process_invoice")
        >>> result = adapter.invoke({"document": "..."})

        >>> # Async handler
        >>> adapter.load("app.service:async_process")
        >>> result = adapter.invoke({"query": "hello"})  # Handles async internally

        >>> # Handler with StreamContext
        >>> result = adapter.invoke({"query": "hello"}, context=stream_context)
    """

    def __init__(self):
        """Initialize handler adapter."""
        self._handler: Optional[Callable] = None
        self._handler_path: Optional[str] = None
        self._is_async: bool = False
        self._signature: Optional[inspect.Signature] = None
        self._accepts_context: bool = False

        logger.debug("HandlerAdapter initialized")

    def load(self, entrypoint: str) -> None:
        """
        Load handler function from path.

        Process:
        1. Validate handler path format (module:callable)
        2. Import module dynamically
        3. Get callable from module
        4. Validate it's actually callable
        5. Detect if async
        6. Store for invocations

        Args:
            entrypoint: Format "module.path:callable_name"
                        Example: "app.service:process_request"

        Raises:
            AdapterLoadError: If loading fails
            ModuleNotFoundError: If module can't be imported
            CallableNotFoundError: If callable doesn't exist
            InvalidAgentError: If target is not callable

        Examples:
            >>> adapter = HandlerAdapter()
            >>> adapter.load("myapp.handlers:process_invoice")
        """
        handler_path = entrypoint  # Alias for clarity in handler context
        logger.info("Loading handler", handler_path=handler_path)

        # Step 1: Validate and parse handler path
        try:
            module_path, callable_name = validate_handler(handler_path)
        except Exception as e:
            logger.error("Invalid handler format", handler_path=handler_path, error=str(e))
            raise AdapterLoadError(
                f"Invalid handler format: {handler_path}. "
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

        # Step 3: Get callable from module
        if not hasattr(module, callable_name):
            available = [name for name in dir(module) if not name.startswith("_")]
            logger.error(
                "Callable not found in module",
                module=module_path,
                callable=callable_name,
                available=available[:10],
            )
            raise CallableNotFoundError(
                module_path=module_path, callable_name=callable_name, available=available[:10]
            )

        try:
            handler = getattr(module, callable_name)
            logger.debug("Handler function found", callable=callable_name)
        except Exception as e:
            logger.error("Failed to get callable", callable=callable_name, error=str(e))
            raise AdapterLoadError(
                f"Failed to get callable '{callable_name}' from module '{module_path}': {e}"
            ) from e

        # Step 4: Validate it's callable
        if not callable(handler):
            handler_type = type(handler).__name__
            logger.error("Handler is not callable", handler_type=handler_type)
            raise InvalidAgentError(
                f"Handler must be a callable function. Got type: {handler_type}. "
                f"Hint: Ensure '{callable_name}' is a function, not a class or variable."
            )

        # Step 5: Detect if async
        self._is_async = asyncio.iscoroutinefunction(handler)

        # Step 6: Get signature for validation and detect context support
        try:
            self._signature = inspect.signature(handler)
            # Check if handler accepts a 'context' parameter specifically
            # Only consider it as accepting context if:
            # 1. There's a parameter explicitly named "context", OR
            # 2. There's a parameter with StreamContext type annotation
            self._accepts_context = False
            for param_name, param in self._signature.parameters.items():
                if param_name == "context":
                    self._accepts_context = True
                    break
                # Check for StreamContext type annotation
                if param.annotation != inspect.Parameter.empty:
                    annotation_str = str(param.annotation)
                    if "StreamContext" in annotation_str:
                        self._accepts_context = True
                        break
        except (ValueError, TypeError):
            logger.warning("Could not inspect handler signature")
            self._signature = None
            self._accepts_context = False

        # Step 7: Store handler
        self._handler = handler
        self._handler_path = handler_path

        logger.info(
            "✅ Handler loaded successfully",
            handler_path=handler_path,
            is_async=self._is_async,
            accepts_context=self._accepts_context,
            signature=str(self._signature) if self._signature else "unknown",
        )

    def invoke(self, payload: Dict[str, Any], context: Optional[Any] = None) -> Dict[str, Any]:
        """
        Invoke handler with payload and optional StreamContext.

        Handles both sync and async handlers automatically.
        If the handler accepts a context parameter and one is provided,
        it will be passed to the handler.

        Args:
            payload: Input dictionary to pass to handler
            context: Optional StreamContext for streaming support

        Returns:
            Output dictionary from handler

        Raises:
            AdapterNotLoadedError: If load() not called
            AgentExecutionError: If handler invocation fails
            InvalidOutputError: If handler returns non-dict

        Examples:
            >>> result = adapter.invoke({"document": "INVOICE #123..."})
            >>> print(result)
            {"vendor": "Acme Corp", "total": 1234.56}

            >>> # With StreamContext
            >>> result = adapter.invoke({"query": "hello"}, context=stream_context)
        """
        # Check adapter is loaded
        if self._handler is None:
            logger.error("Invoke called before load")
            raise AdapterNotLoadedError()

        logger.debug(
            "Handler invocation started",
            handler_path=self._handler_path,
            input_keys=list(payload.keys()) if isinstance(payload, dict) else "non-dict",
            is_async=self._is_async,
            has_context=context is not None,
        )

        # Set thread-local context if provided
        if context is not None:
            try:
                from dockrion_events import set_current_context

                set_current_context(context)
            except ImportError:
                pass  # Events package not installed

        # Invoke handler
        try:
            if self._is_async:
                # Handle async function
                result = self._invoke_async(payload, context)
            else:
                # Handle sync function - pass context if handler accepts it
                if self._accepts_context and context is not None:
                    result = self._handler(payload, context)
                else:
                    result = self._handler(payload)

        except TypeError as e:
            logger.error(
                "Handler invocation failed with TypeError",
                error=str(e),
                payload_type=type(payload).__name__,
            )
            raise AgentExecutionError(
                f"Handler invocation failed with TypeError: {e}. "
                f"Hint: Ensure handler signature matches: def handler(payload: dict) -> dict"
            ) from e
        except Exception as e:
            logger.error(
                "Handler invocation failed",
                error=str(e),
                error_type=type(e).__name__,
                handler_path=self._handler_path,
            )
            raise AgentExecutionError(f"Handler invocation failed: {type(e).__name__}: {e}") from e
        finally:
            # Clear thread-local context
            if context is not None:
                try:
                    from dockrion_events import set_current_context

                    set_current_context(None)
                except ImportError:
                    pass

        # Validate output is dict
        if not isinstance(result, dict):
            actual_type = type(result).__name__
            logger.error(
                "Handler returned non-dict output",
                actual_type=actual_type,
                handler_path=self._handler_path,
            )
            raise InvalidOutputError(
                f"Handler must return dict, got {actual_type}. "
                f"Hint: Ensure your handler returns a dictionary.",
                actual_type=type(result),
            )

        # Deep serialize result to ensure JSON-serializable output
        result = serialize_for_json(result)

        logger.debug(
            "Handler invocation completed",
            handler_path=self._handler_path,
            output_keys=list(result.keys()),
        )

        return result

    def _invoke_async(
        self, payload: Dict[str, Any], context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Invoke async handler, running event loop if needed.

        Args:
            payload: Input dictionary
            context: Optional StreamContext

        Returns:
            Output dictionary from async handler
        """
        # Capture handler reference for thread-safe closure
        handler = self._handler
        accepts_context = self._accepts_context
        assert handler is not None, "Handler not loaded"

        def run_in_new_loop() -> Dict[str, Any]:
            """Run the async handler in a fresh event loop (for executor thread)."""
            if accepts_context and context is not None:
                return asyncio.run(handler(payload, context))
            return asyncio.run(handler(payload))

        try:
            # Try to get running loop
            asyncio.get_running_loop()
            # We're already in an async context - run in separate thread
            # to avoid nested event loop issues
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Defer coroutine creation until inside executor thread
                future = executor.submit(run_in_new_loop)
                return future.result()
        except RuntimeError:
            # No running loop - create one directly
            if accepts_context and context is not None:
                return asyncio.run(handler(payload, context))
            return asyncio.run(handler(payload))

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get adapter metadata for introspection.

        Returns:
            Metadata dictionary with adapter and handler information

        Examples:
            >>> metadata = adapter.get_metadata()
            >>> print(metadata)
            {
                'framework': 'custom',
                'adapter_type': 'handler',
                'adapter_version': '0.1.0',
                'loaded': True,
                'handler_path': 'app.service:process_request',
                'is_async': False,
                'accepts_context': True
            }
        """
        return {
            "framework": "custom",
            "adapter_type": "handler",
            "adapter_version": "0.1.0",
            "loaded": self._handler is not None,
            "handler_path": self._handler_path,
            "is_async": self._is_async,
            "accepts_context": self._accepts_context,
            "signature": str(self._signature) if self._signature else None,
        }

    def health_check(self) -> bool:
        """
        Quick health check for adapter.

        Returns:
            True if handler is loaded, False otherwise
        """
        return self._handler is not None

    async def invoke_stream(
        self,
        payload: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Any] = None,
        events_filter: Optional[Any] = None,
    ):
        """
        Stream handler execution, yielding events as they occur.

        Since handlers are typically simple functions, this implementation
        wraps the invoke method and yields the result as a single event.
        However, if a context is provided (queue mode), any user-emitted
        events during execution will be yielded afterward.

        Args:
            payload: Input dictionary
            config: Optional configuration (unused for handlers)
            context: Optional StreamContext for emitting events
            events_filter: Optional EventsFilter to control which events are yielded

        Yields:
            Dictionaries containing the result and any user-emitted events

        Example:
            >>> async for event in adapter.invoke_stream(payload):
            ...     print(f"Event: {event.get('type')}")
        """
        import uuid as uuid_module

        from dockrion_common import get_logger

        logger = get_logger("handler-adapter")

        # Create queue-mode context if not provided but filter is available
        stream_context = context
        owns_context = False
        if stream_context is None and events_filter is not None:
            try:
                from dockrion_events import StreamContext

                run_id = str(uuid_module.uuid4())
                stream_context = StreamContext(
                    run_id=run_id,
                    queue_mode=True,
                    events_filter=events_filter,
                )
                owns_context = True
                logger.debug(
                    "Created queue-mode context for Pattern A",
                    run_id=run_id,
                )
            except ImportError:
                pass

        try:
            # Invoke the handler (context is passed if supported)
            result = self.invoke(payload, context=stream_context)

            # Yield the result
            yield {"type": "result", "data": result}

            # Drain any user-emitted events from context queue
            if stream_context is not None and hasattr(stream_context, "drain_queued_events"):
                try:
                    user_events = stream_context.drain_queued_events()
                    for event in user_events:
                        yield {
                            "type": "custom",
                            "event_type": getattr(event, "type", "custom"),
                            "data": event.model_dump() if hasattr(event, "model_dump") else {},
                        }
                except Exception as e:
                    logger.debug(f"Failed to drain user events: {e}")

        finally:
            # Clean up owned context
            if owns_context and stream_context is not None:
                try:
                    from dockrion_events import set_current_context

                    set_current_context(None)
                except ImportError:
                    pass
