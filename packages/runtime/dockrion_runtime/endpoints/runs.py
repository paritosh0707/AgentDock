"""
Runs Endpoints

Provides the async runs API (Pattern B) for starting runs and subscribing to events.

Endpoints:
    POST /runs              - Start an async run
    GET /runs/{run_id}      - Get run status and result
    GET /runs/{run_id}/events - Subscribe to events (SSE)
    DELETE /runs/{run_id}   - Cancel a running execution
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, Optional, Type

if TYPE_CHECKING:
    pass  # For future type imports

from dockrion_common.errors import ValidationError
from dockrion_common.http_models import ErrorResponse
from dockrion_common.logger import get_logger
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from ..auth import AuthContext
from ..config import RuntimeConfig, RuntimeState

logger = get_logger(__name__)


def create_runs_router(
    config: RuntimeConfig,
    state: RuntimeState,
    auth_dependency: Callable[[Request], Awaitable[AuthContext]],
    input_model: Type[BaseModel],
    output_model: Type[BaseModel],
) -> APIRouter:
    """
    Create router for async runs endpoints.

    Args:
        config: Runtime configuration
        state: Runtime state
        auth_dependency: Authentication dependency function
        input_model: Dynamic Pydantic model for request payload
        output_model: Dynamic Pydantic model for response output

    Returns:
        APIRouter with runs endpoints
    """
    router = APIRouter(prefix="/runs", tags=["runs"])

    @router.post(
        "",
        status_code=202,
        responses={
            202: {"description": "Run accepted and started"},
            400: {"model": ErrorResponse, "description": "Validation error"},
            500: {"model": ErrorResponse, "description": "Server error"},
        },
    )
    async def create_run(
        request: Request,
        payload: input_model = Body(..., description="Agent input payload"),  # type: ignore[valid-type]
        run_id: Optional[str] = Query(None, description="Optional client-provided run ID"),
        auth_context: AuthContext = Depends(auth_dependency),
    ) -> JSONResponse:
        """
        Start an async agent execution.

        Returns immediately with a run ID that can be used to:
        - Subscribe to events via GET /runs/{run_id}/events
        - Check status via GET /runs/{run_id}
        - Cancel via DELETE /runs/{run_id}
        """
        assert state.run_manager is not None, "Run manager not initialized"
        assert state.adapter is not None, "Adapter not initialized"
        assert state.policy_engine is not None, "Policy engine not initialized"
        assert state.metrics is not None, "Metrics not initialized"

        try:
            # Create run
            run = await state.run_manager.create_run(
                run_id=run_id,
                agent_name=config.agent_name,
                framework=config.agent_framework,
            )

            # Convert Pydantic model to dict
            payload_dict: Dict[str, Any] = (
                payload.model_dump()  # type: ignore[attr-defined]
                if hasattr(payload, "model_dump")
                else payload.dict()  # type: ignore[attr-defined]
            )

            # Apply input policies
            payload_dict = state.policy_engine.validate_input(payload_dict)

            logger.info(
                "Run created",
                run_id=run.run_id,
                payload_keys=list(payload_dict.keys()),
            )

            # Start execution in background
            asyncio.create_task(
                _execute_run(
                    run_id=run.run_id,
                    payload=payload_dict,
                    config=config,
                    state=state,
                )
            )

            return JSONResponse(
                status_code=202,
                content={
                    "run_id": run.run_id,
                    "status": "accepted",
                    "events_url": f"/runs/{run.run_id}/events",
                    "created_at": run.created_at.isoformat(),
                },
            )

        except ValidationError as e:
            logger.warning(f"Run creation failed: {e}")
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(error=str(e), code="VALIDATION_ERROR").model_dump(),
            )
        except Exception as e:
            logger.error(f"Run creation failed: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(error=str(e), code="INTERNAL_ERROR").model_dump(),
            )

    @router.get(
        "/{run_id}",
        responses={
            200: {"description": "Run status and result"},
            404: {"model": ErrorResponse, "description": "Run not found"},
        },
    )
    async def get_run_status(
        run_id: str,
        auth_context: AuthContext = Depends(auth_dependency),
    ) -> JSONResponse:
        """
        Get the current status and result of a run.
        """
        assert state.run_manager is not None, "Run manager not initialized"

        run = await state.run_manager.get_run(run_id)
        if not run:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error=f"Run '{run_id}' not found",
                    code="NOT_FOUND",
                ).model_dump(),
            )

        return JSONResponse(status_code=200, content=run.to_response())

    @router.get(
        "/{run_id}/events",
        responses={
            200: {"description": "SSE event stream"},
            404: {"model": ErrorResponse, "description": "Run not found"},
        },
    )
    async def subscribe_events(
        run_id: str,
        timeout: int = Query(
            default=300, ge=1, le=3600, description="Connection timeout (seconds)"
        ),
        from_sequence: int = Query(default=0, ge=0, description="Resume from sequence number"),
        auth_context: AuthContext = Depends(auth_dependency),
    ):
        """
        Subscribe to events for a run via Server-Sent Events (SSE).

        The connection will:
        - Replay any stored events from `from_sequence` (if > 0)
        - Stream live events as they occur
        - Close when a terminal event (complete, error, cancelled) is received
        - Close after `timeout` seconds of inactivity
        """
        assert state.run_manager is not None, "Run manager not initialized"
        assert state.event_bus is not None, "Event bus not initialized"

        # Check run exists
        run = await state.run_manager.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

        # Capture event_bus in local variable for type narrowing in generator
        event_bus = state.event_bus

        async def event_generator():
            """Generate SSE events."""
            from dockrion_events import is_terminal_event

            start_time = time.time()
            last_event_time = start_time

            try:
                # Subscribe to events (includes stored events if from_sequence > 0)
                async for event in event_bus.subscribe(
                    run_id,
                    from_sequence=from_sequence,
                    include_stored=(from_sequence > 0),
                ):
                    # Yield event in SSE format
                    yield event.to_sse()
                    last_event_time = time.time()

                    # Check for terminal event
                    if is_terminal_event(event):
                        logger.debug(
                            "Terminal event received, closing stream",
                            run_id=run_id,
                            event_type=event.type,
                        )
                        break

                    # Check timeout
                    if time.time() - start_time > timeout:
                        logger.debug(
                            "SSE timeout reached",
                            run_id=run_id,
                            timeout=timeout,
                        )
                        yield 'event: timeout\ndata: {"message": "Connection timeout"}\n\n'
                        break

            except asyncio.CancelledError:
                logger.debug("SSE connection cancelled", run_id=run_id)
            except Exception as e:
                logger.error(
                    "SSE error",
                    run_id=run_id,
                    error=str(e),
                    exc_info=True,
                )
                yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    @router.delete(
        "/{run_id}",
        responses={
            200: {"description": "Run cancelled"},
            404: {"model": ErrorResponse, "description": "Run not found"},
            400: {"model": ErrorResponse, "description": "Run already finished"},
        },
    )
    async def cancel_run(
        run_id: str,
        reason: Optional[str] = Query(None, description="Cancellation reason"),
        auth_context: AuthContext = Depends(auth_dependency),
    ) -> JSONResponse:
        """
        Cancel a running execution.
        """
        assert state.run_manager is not None, "Run manager not initialized"

        try:
            await state.run_manager.cancel_run(
                run_id, reason=reason or "User requested cancellation"
            )

            return JSONResponse(
                status_code=200,
                content={
                    "run_id": run_id,
                    "status": "cancelled",
                },
            )

        except ValidationError as e:
            if "not found" in str(e).lower():
                return JSONResponse(
                    status_code=404,
                    content=ErrorResponse(error=str(e), code="NOT_FOUND").model_dump(),
                )
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(error=str(e), code="VALIDATION_ERROR").model_dump(),
            )
        except Exception as e:
            logger.error(f"Cancel run failed: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(error=str(e), code="INTERNAL_ERROR").model_dump(),
            )

    return router


async def _execute_run(
    run_id: str,
    payload: Dict[str, Any],
    config: RuntimeConfig,
    state: RuntimeState,
) -> None:
    """
    Execute a run in the background.

    This function:
    1. Starts the run (emits 'started' event)
    2. Gets StreamContext for emitting intermediate events (with filter)
    3. Invokes the adapter with context (enables token/progress events)
    4. Sets result or error (emits 'complete' or 'error' event)

    The context parameter enables the adapter to emit intermediate events
    (tokens, progress, steps) that are published to the EventBus and
    streamed to subscribers via SSE.

    Event filtering from Dockfile configuration is applied:
    - If streaming.events.allowed is configured, only those events are emitted
    - Mandatory events (started, complete, error, cancelled) are always emitted
    """
    assert state.run_manager is not None
    assert state.adapter is not None
    assert state.policy_engine is not None
    assert state.metrics is not None

    start_time = time.time()
    state.metrics.inc_active()

    # Get events filter from config
    events_filter = config.streaming.get_events_filter()

    try:
        # Start run (emits 'started' event)
        await state.run_manager.start_run(run_id)

        # Get context for emitting events - this is the key piece!
        # The context allows the adapter to emit intermediate events
        # Pass events_filter to filter events at emission time
        context = await state.run_manager.get_context(run_id, events_filter=events_filter)

        # Invoke adapter
        logger.debug(f"Executing run {run_id} with streaming context...")

        # Capture references for thread-safe closure
        adapter = state.adapter

        # Check if adapter supports streaming for richer event output
        supports_streaming = hasattr(adapter, "invoke_stream") and callable(
            getattr(adapter, "invoke_stream", None)
        )

        if supports_streaming:
            # Use streaming invocation for step-by-step events
            result = await _execute_with_streaming(
                adapter=adapter,
                payload=payload,
                context=context,
                config=config,
                run_id=run_id,
            )
        else:
            # Use regular invocation with context for event emission
            result = await _execute_with_invoke(
                adapter=adapter,
                payload=payload,
                context=context,
                config=config,
                run_id=run_id,
            )

        # Apply output policies
        result = state.policy_engine.apply_output_policies(result)

        latency = time.time() - start_time

        # Set result (emits 'complete' event)
        await state.run_manager.set_result(
            run_id,
            output=result,
            latency_seconds=round(latency, 3),
            metadata={
                "agent": config.agent_name,
                "framework": config.agent_framework,
            },
        )

        state.metrics.inc_request("invoke", "success")
        state.metrics.observe_latency("invoke", latency)
        logger.info(f"Run {run_id} completed in {latency:.3f}s")

    except asyncio.TimeoutError:
        latency = time.time() - start_time
        logger.warning(f"Run {run_id} timed out after {config.timeout_sec}s")

        try:
            await state.run_manager.set_error(
                run_id,
                error=f"Agent invocation timed out after {config.timeout_sec}s",
                code="TIMEOUT_ERROR",
            )
        except Exception:
            pass  # Best effort

        state.metrics.inc_request("invoke", "timeout")

    except Exception as e:
        latency = time.time() - start_time
        logger.error(f"Run {run_id} failed: {e}", exc_info=True)

        try:
            await state.run_manager.set_error(
                run_id,
                error=str(e),
                code=getattr(e, "code", "INTERNAL_ERROR"),
            )
        except Exception:
            pass  # Best effort

        state.metrics.inc_request("invoke", "error")

    finally:
        state.metrics.dec_active()


async def _execute_with_invoke(
    adapter: Any,
    payload: Dict[str, Any],
    context: Any,
    config: RuntimeConfig,
    run_id: str,
) -> Dict[str, Any]:
    """
    Execute adapter using invoke() with context.

    Runs the synchronous invoke() in a thread pool executor to avoid
    blocking the event loop. The context is passed to enable intermediate
    event emission.

    Args:
        adapter: The loaded adapter instance
        payload: Input payload dictionary
        context: StreamContext for event emission
        config: Runtime configuration
        run_id: The run ID for logging

    Returns:
        Result dictionary from the adapter
    """
    import functools

    # Create a wrapper function that captures context properly
    # Using functools.partial ensures variables are captured by value
    def invoke_with_context(
        _adapter: Any, _payload: Dict[str, Any], _context: Any
    ) -> Dict[str, Any]:
        """Invoke adapter with context in executor thread."""
        return _adapter.invoke(_payload, context=_context)

    # Use functools.partial for proper variable capture in the executor
    invoke_fn = functools.partial(invoke_with_context, adapter, payload, context)

    if config.timeout_sec > 0:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, invoke_fn),
            timeout=config.timeout_sec,
        )
    else:
        result = await asyncio.get_event_loop().run_in_executor(None, invoke_fn)

    return result


async def _execute_with_streaming(
    adapter: Any,
    payload: Dict[str, Any],
    context: Any,
    config: RuntimeConfig,
    run_id: str,
) -> Dict[str, Any]:
    """
    Execute adapter using invoke_stream() for richer events.

    Uses the adapter's streaming capability to emit step-by-step events.
    Each step from the stream is automatically published to the EventBus
    via the context.

    Args:
        adapter: The loaded adapter instance (must have invoke_stream)
        payload: Input payload dictionary
        context: StreamContext for event emission
        config: Runtime configuration
        run_id: The run ID for logging

    Returns:
        Final result dictionary (last output from stream)
    """
    result: Dict[str, Any] = {}

    try:
        if config.timeout_sec > 0:
            # Wrap the async iteration with a timeout
            async def stream_with_timeout():
                nonlocal result
                async for chunk in adapter.invoke_stream(payload, context=context):
                    if isinstance(chunk, dict):
                        # Track the latest result
                        if chunk.get("type") == "result":
                            result = chunk.get("data", chunk)
                        elif "output" in chunk:
                            result = chunk.get("output", chunk)
                        else:
                            # For step events, keep accumulating
                            result = chunk
                return result

            result = await asyncio.wait_for(
                stream_with_timeout(),
                timeout=config.timeout_sec,
            )
        else:
            async for chunk in adapter.invoke_stream(payload, context=context):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "result":
                        result = chunk.get("data", chunk)
                    elif "output" in chunk:
                        result = chunk.get("output", chunk)
                    else:
                        result = chunk

    except asyncio.TimeoutError:
        raise  # Re-raise to be handled by caller

    # If result is empty, try a regular invoke as fallback
    if not result:
        logger.warning(
            f"Streaming returned no result for run {run_id}, falling back to invoke"
        )
        result = await _execute_with_invoke(adapter, payload, context, config, run_id)

    return result
