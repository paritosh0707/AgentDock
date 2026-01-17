"""
Invoke Endpoints

Provides the main agent invocation endpoints (sync and streaming).
"""

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Type, Union

from dockrion_common.errors import DockrionError, ValidationError
from dockrion_common.http_models import ErrorResponse
from dockrion_common.logger import get_logger
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, create_model

from ..auth import AuthContext
from ..config import RuntimeConfig, RuntimeState

logger = get_logger(__name__)


def create_invoke_router(
    config: RuntimeConfig,
    state: RuntimeState,
    auth_dependency: Callable[[Request], Awaitable[AuthContext]],
    input_model: Type[BaseModel],
    output_model: Type[BaseModel],
    strict_output_validation: bool = True,
) -> APIRouter:
    """
    Create router for invoke endpoints.

    Args:
        config: Runtime configuration
        state: Runtime state
        auth_dependency: Authentication dependency function
        input_model: Dynamic Pydantic model for request payload (from io_schema.input)
        output_model: Dynamic Pydantic model for response output (from io_schema.output)

    Returns:
        APIRouter with invoke endpoints
    """
    router = APIRouter(tags=["invoke"])

    # Create dynamic response model with typed output
    agent_name_clean = config.agent_name.replace("-", "_").replace(".", "_").capitalize()

    InvokeResponseModel: Type[BaseModel] = create_model(
        f"{agent_name_clean}InvokeResponse",
        success=(bool, True),
        output=(output_model, ...),
        metadata=(Dict[str, Any], ...),
    )

    @router.post(
        "/invoke",
        response_model=InvokeResponseModel,
        responses={
            400: {"model": ErrorResponse, "description": "Validation error"},
            500: {"model": ErrorResponse, "description": "Server error"},
        },
    )
    async def invoke_agent(
        payload: input_model = Body(..., description="Agent input payload"),  # type: ignore[valid-type]
        auth_context: AuthContext = Depends(auth_dependency),
    ) -> Union[BaseModel, JSONResponse]:
        """
        Invoke the agent with the given payload.

        The adapter layer handles framework-specific invocation logic.
        Request body is automatically validated against the input schema.
        """
        assert state.metrics is not None
        assert state.policy_engine is not None
        assert state.adapter is not None

        state.metrics.inc_active()
        start_time = time.time()

        try:
            # Convert Pydantic model to dict
            payload_dict: Dict[str, Any] = (
                payload.model_dump()  # type: ignore[attr-defined]
                if hasattr(payload, "model_dump")
                else payload.dict()  # type: ignore[attr-defined]
            )

            logger.info(
                "📥 Invoke request received", extra={"payload_keys": list(payload_dict.keys())}
            )

            # Apply input policies
            payload_dict = state.policy_engine.validate_input(payload_dict)

            # Invoke agent via adapter
            logger.debug(f"Invoking {config.agent_framework} agent...")

            # Capture adapter reference for lambda
            adapter = state.adapter

            if config.timeout_sec > 0:
                try:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: adapter.invoke(payload_dict)
                        ),
                        timeout=config.timeout_sec,
                    )
                except asyncio.TimeoutError:
                    raise DockrionError(f"Agent invocation timed out after {config.timeout_sec}s")
            else:
                result = adapter.invoke(payload_dict)

            # Apply output policies
            result = state.policy_engine.apply_output_policies(result)

            latency = time.time() - start_time

            # Record metrics
            state.metrics.inc_request("invoke", "success")
            state.metrics.observe_latency("invoke", latency)

            logger.info(f"✅ Invoke completed in {latency:.3f}s")

            # Validate output against schema (if strict mode enabled)
            if strict_output_validation:
                try:
                    typed_output: Any = (
                        output_model(**result) if isinstance(result, dict) else result
                    )
                except Exception:
                    # If output doesn't match schema, use raw result
                    typed_output = result
            else:
                # Lenient mode: skip output validation
                typed_output = result

            return InvokeResponseModel(
                success=True,
                output=typed_output,
                metadata={
                    "agent": config.agent_name,
                    "framework": config.agent_framework,
                    "latency_seconds": round(latency, 3),
                },
            )

        except ValidationError as e:
            state.metrics.inc_request("invoke", "validation_error")
            logger.warning(f"⚠️ Validation error: {e}")
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(error=str(e), code="VALIDATION_ERROR").model_dump(),
            )

        except DockrionError as e:
            state.metrics.inc_request("invoke", "dockrion_error")
            logger.error(f"❌ Dockrion error: {e}")
            return JSONResponse(
                status_code=500, content=ErrorResponse(error=e.message, code=e.code).model_dump()
            )

        except Exception as e:
            state.metrics.inc_request("invoke", "error")
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(error=str(e), code="INTERNAL_ERROR").model_dump(),
            )

        finally:
            state.metrics.dec_active()

    # Streaming endpoint (if enabled)
    if config.enable_streaming:

        @router.post("/invoke/stream")
        async def invoke_agent_stream(
            payload: input_model = Body(..., description="Agent input payload"),  # type: ignore[valid-type]
            auth_context: AuthContext = Depends(auth_dependency),
        ):
            """
            Invoke the agent with streaming response (SSE).

            This is Pattern A (Direct Streaming): the client receives events
            in the same connection as the invocation request.

            **Key differences from Pattern B (/runs):**
            - Uses `request_id` (not `run_id`) - this is a correlation ID only
            - No server-side persistence - events are not stored
            - No resumability - if connection drops, events are lost
            - Lowest latency - direct streaming without EventBus overhead

            For managed runs with persistence, resumability, and event replay,
            use Pattern B: POST /runs + GET /runs/{run_id}/events

            Event filtering is applied based on Dockfile configuration:
            - If streaming.events.allowed is configured, only those events are emitted
            - Mandatory events (started, complete, error, cancelled) are always emitted
            """
            import uuid as uuid_module

            assert state.metrics is not None
            assert state.policy_engine is not None
            assert state.adapter is not None

            # Capture references for closure
            metrics = state.metrics
            adapter = state.adapter

            # Get events filter from config
            events_filter = config.streaming.get_events_filter()

            metrics.inc_active()
            start_time = time.time()

            try:
                # Convert Pydantic model to dict
                payload_dict: Dict[str, Any] = (
                    payload.model_dump()  # type: ignore[attr-defined]
                    if hasattr(payload, "model_dump")
                    else payload.dict()  # type: ignore[attr-defined]
                )

                # Apply input policies
                payload_dict = state.policy_engine.validate_input(payload_dict)

                # Generate a request ID for client-side correlation
                # Note: This is NOT a run_id - Pattern A (direct streaming) does not create
                # persistent runs. Use Pattern B (/runs) for managed runs with resumability.
                request_id = str(uuid_module.uuid4())

                async def event_generator() -> AsyncGenerator[str, None]:
                    nonlocal start_time

                    # Emit started event (mandatory, always allowed)
                    yield f"event: started\ndata: {json.dumps({'request_id': request_id, 'type': 'started'})}\n\n"

                    try:
                        # Check if adapter supports streaming
                        if hasattr(adapter, "invoke_stream"):
                            # Pass events_filter to adapter for filtering at source
                            async for chunk in adapter.invoke_stream(  # type: ignore[attr-defined]
                                payload_dict,
                                events_filter=events_filter,
                            ):
                                if isinstance(chunk, dict):
                                    event_type = chunk.get("type", "step")

                                    # Check if this event type is allowed
                                    if events_filter is not None:
                                        custom_name = chunk.get("event_type") if event_type == "custom" else None
                                        if not events_filter.is_allowed(event_type, custom_name):
                                            continue

                                    chunk["request_id"] = request_id
                                    yield f"event: {event_type}\ndata: {json.dumps(chunk)}\n\n"
                                else:
                                    # Token event
                                    if events_filter is None or events_filter.is_allowed("token"):
                                        yield f"event: token\ndata: {json.dumps({'request_id': request_id, 'content': str(chunk)})}\n\n"
                        else:
                            # Non-streaming adapter: invoke and emit result
                            result = adapter.invoke(payload_dict)

                            # Apply output policies
                            result = state.policy_engine.apply_output_policies(result)

                            latency = time.time() - start_time

                            # Emit complete event (mandatory, always allowed)
                            yield f"event: complete\ndata: {json.dumps({'request_id': request_id, 'type': 'complete', 'output': result, 'latency_seconds': round(latency, 3)})}\n\n"

                            metrics.inc_request("invoke", "success")
                            metrics.observe_latency("invoke", latency)
                            return

                        # If we used streaming, emit complete at the end (mandatory)
                        latency = time.time() - start_time
                        yield f"event: complete\ndata: {json.dumps({'request_id': request_id, 'type': 'complete', 'latency_seconds': round(latency, 3)})}\n\n"
                        metrics.inc_request("invoke", "success")
                        metrics.observe_latency("invoke", latency)

                    except Exception as e:
                        metrics.inc_request("invoke", "error")
                        logger.error(f"Streaming invoke error: {e}", exc_info=True)
                        # Error event is mandatory, always emitted
                        yield f"event: error\ndata: {json.dumps({'request_id': request_id, 'type': 'error', 'error': str(e), 'code': 'INTERNAL_ERROR'})}\n\n"
                    finally:
                        metrics.dec_active()

                return StreamingResponse(
                    event_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",  # Disable nginx buffering
                    },
                )

            except Exception as e:
                metrics.dec_active()
                raise HTTPException(status_code=500, detail=str(e))

    return router
