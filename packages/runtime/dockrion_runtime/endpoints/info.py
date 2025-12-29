"""
Info and Schema Endpoints

Provides agent information and schema introspection endpoints.
"""

from typing import Any, Dict

from dockrion_common.http_models import InfoResponse, SchemaResponse
from dockrion_schema import DockSpec
from fastapi import APIRouter

from ..config import RuntimeConfig


def create_info_router(config: RuntimeConfig, spec: DockSpec) -> APIRouter:
    """
    Create router for info/schema endpoints.

    Args:
        config: Runtime configuration
        spec: DockSpec with schema information

    Returns:
        APIRouter with info endpoints
    """
    router = APIRouter(tags=["info"])

    @router.get("/schema", response_model=SchemaResponse)
    async def get_schema() -> SchemaResponse:
        """Get the input/output schema for this agent."""
        io_schema = spec.io_schema
        return SchemaResponse(
            agent=config.agent_name,
            input_schema=io_schema.input.model_dump() if io_schema and io_schema.input else {},
            output_schema=io_schema.output.model_dump() if io_schema and io_schema.output else {},
        )

    @router.get("/info", response_model=InfoResponse)
    async def get_info() -> InfoResponse:
        """Get agent metadata and configuration."""
        # Build agent info based on invocation mode
        agent_info: Dict[str, Any] = {
            "name": config.agent_name,
            "description": config.agent_description,
            "framework": config.agent_framework,
            "mode": "handler" if config.use_handler_mode else "entrypoint",
            "target": config.invocation_target,
        }

        # Include mode-specific field for clarity
        if config.use_handler_mode and config.agent_handler:
            agent_info["handler"] = config.agent_handler
        elif config.agent_entrypoint:
            agent_info["entrypoint"] = config.agent_entrypoint

        # Get optional metadata
        metadata = spec.metadata.model_dump() if spec.metadata else None

        return InfoResponse(
            agent=agent_info,
            auth_enabled=config.auth_enabled,
            version=config.version,
            metadata=metadata,
        )

    return router
