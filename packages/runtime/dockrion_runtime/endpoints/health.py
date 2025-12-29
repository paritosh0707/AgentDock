"""
Health and Metrics Endpoints

Provides health check, readiness check, and Prometheus metrics endpoints.
"""

import time

from dockrion_common.http_models import HealthResponse, ReadyResponse
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..config import RuntimeConfig, RuntimeState


def create_health_router(config: RuntimeConfig, state: RuntimeState) -> APIRouter:
    """
    Create router for health-related endpoints.

    Args:
        config: Runtime configuration
        state: Runtime state

    Returns:
        APIRouter with health endpoints
    """
    router = APIRouter(tags=["health"])

    @router.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check for load balancers and orchestrators."""
        return HealthResponse(
            status="ok",
            service=f"runtime:{config.agent_name}",
            version=config.version,
            timestamp=time.time(),
            agent=config.agent_name,
            framework=config.agent_framework,
        )

    @router.get("/ready", response_model=ReadyResponse)
    async def readiness_check() -> ReadyResponse:
        """Readiness check - verifies agent is fully initialized."""
        if not state.ready or state.adapter is None:
            raise HTTPException(status_code=503, detail="Agent not ready")
        return ReadyResponse(status="ready", agent=config.agent_name)

    @router.get("/metrics")
    async def prometheus_metrics():
        """Prometheus metrics endpoint."""
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return router
