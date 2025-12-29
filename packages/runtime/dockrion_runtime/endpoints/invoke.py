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

            # Validate output against schema and return typed response
            try:
                typed_output: Any = output_model(**result) if isinstance(result, dict) else result
            except Exception:
                # If output doesn't match schema, use raw result
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
            """Invoke the agent with streaming response (SSE)."""
            assert state.metrics is not None
            assert state.policy_engine is not None
            assert state.adapter is not None

            # Capture references for closure
            metrics = state.metrics
            adapter = state.adapter

            metrics.inc_active()

            try:
                # Convert Pydantic model to dict
                payload_dict: Dict[str, Any] = (
                    payload.model_dump()  # type: ignore[attr-defined]
                    if hasattr(payload, "model_dump")
                    else payload.dict()  # type: ignore[attr-defined]
                )

                # Apply input policies
                payload_dict = state.policy_engine.validate_input(payload_dict)

                async def event_generator() -> AsyncGenerator[str, None]:
                    try:
                        if hasattr(adapter, "invoke_stream"):
                            async for chunk in adapter.invoke_stream(payload_dict):  # type: ignore[attr-defined]
                                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        else:
                            result = adapter.invoke(payload_dict)
                            yield f"data: {json.dumps({'output': result})}\n\n"

                        yield f"data: {json.dumps({'done': True})}\n\n"

                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    finally:
                        metrics.dec_active()

                return StreamingResponse(
                    event_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )

            except Exception as e:
                metrics.dec_active()
                raise HTTPException(status_code=500, detail=str(e))

    return router
