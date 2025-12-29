"""
dockrion HTTP Response Models

This module provides Pydantic response models for consistent API responses across
all dockrion services. Use these models with FastAPI's response_model parameter
for automatic OpenAPI documentation.

Usage:
    from dockrion_common.http_models import (
        InvokeResponse, HealthResponse, ErrorResponse, ReadyResponse,
        SchemaResponse, InfoResponse, PaginatedResponse
    )

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="ok", service="my-service", ...)

    @app.post("/invoke", response_model=InvokeResponse)
    async def invoke():
        return InvokeResponse(output=result, metadata={...})
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """
    Standard error response model.

    Attributes:
        success: Always False for error responses
        error: Error message
        code: Error code for programmatic handling

    Examples:
        >>> response = ErrorResponse(error="Invalid input", code="VALIDATION_ERROR")
        >>> response.model_dump()
        {'success': False, 'error': 'Invalid input', 'code': 'VALIDATION_ERROR'}
    """

    success: bool = False
    error: str
    code: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": False,
                    "error": "Agent name must be lowercase",
                    "code": "VALIDATION_ERROR",
                }
            ]
        }
    )


class PaginatedResponse(BaseModel):
    """
    Standard paginated list response model.

    Attributes:
        success: Always True for success responses
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page

    Examples:
        >>> response = PaginatedResponse(
        ...     items=[{"id": "1"}, {"id": "2"}],
        ...     total=100,
        ...     page=1,
        ...     page_size=10
        ... )
        >>> response.model_dump()
        {'success': True, 'items': [...], 'total': 100, 'page': 1, 'page_size': 10}
    """

    success: bool = True
    items: List[Any]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Check if there is a next page"""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Check if there is a previous page"""
        return self.page > 1

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "items": [{"id": "1", "name": "agent-1"}, {"id": "2", "name": "agent-2"}],
                    "total": 25,
                    "page": 1,
                    "page_size": 10,
                }
            ]
        }
    )


class HealthResponse(BaseModel):
    """
    Standard health check response model.

    Attributes:
        status: Health status ("ok" or "degraded")
        service: Service name
        version: Service version
        timestamp: Unix timestamp of the health check
        agent: Optional agent name (for runtime health checks)
        framework: Optional agent framework (for runtime health checks)

    Examples:
        >>> import time
        >>> response = HealthResponse(
        ...     status="ok",
        ...     service="controller",
        ...     version="1.0.0",
        ...     timestamp=time.time()
        ... )
    """

    status: str  # "ok" or "degraded"
    service: str
    version: str
    timestamp: float
    agent: Optional[str] = None
    framework: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "service": "controller",
                    "version": "1.0.0",
                    "timestamp": 1699456789.123,
                },
                {
                    "status": "ok",
                    "service": "runtime:invoice-copilot",
                    "version": "1.0.0",
                    "timestamp": 1699456789.123,
                    "agent": "invoice-copilot",
                    "framework": "langgraph",
                },
            ]
        }
    )


class InvokeResponse(BaseModel):
    """
    Standard response model for agent invocation.

    Attributes:
        success: Always True for success responses
        output: Agent output (any type)
        metadata: Invocation metadata (agent name, framework, latency, etc.)

    Examples:
        >>> response = InvokeResponse(
        ...     output={"result": "processed"},
        ...     metadata={"agent": "invoice-copilot", "latency_seconds": 0.123}
        ... )
        >>> response.model_dump()
        {'success': True, 'output': {...}, 'metadata': {...}}
    """

    success: bool = True
    output: Any
    metadata: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "output": {"vendor": "Acme Corp", "amount": 1500.00, "currency": "USD"},
                    "metadata": {
                        "agent": "invoice-copilot",
                        "framework": "langgraph",
                        "latency_seconds": 0.523,
                    },
                }
            ]
        }
    )


class ReadyResponse(BaseModel):
    """
    Standard readiness check response model.

    Attributes:
        success: Always True for success responses
        status: Readiness status ("ready")
        agent: Agent name

    Examples:
        >>> response = ReadyResponse(status="ready", agent="invoice-copilot")
        >>> response.model_dump()
        {'success': True, 'status': 'ready', 'agent': 'invoice-copilot'}
    """

    success: bool = True
    status: str  # "ready"
    agent: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"success": True, "status": "ready", "agent": "invoice-copilot"}]
        }
    )


class SchemaResponse(BaseModel):
    """
    Standard schema endpoint response model.

    Attributes:
        success: Always True for success responses
        agent: Agent name
        input_schema: Input JSON schema definition
        output_schema: Output JSON schema definition

    Examples:
        >>> response = SchemaResponse(
        ...     agent="invoice-copilot",
        ...     input_schema={"type": "object", "properties": {...}},
        ...     output_schema={"type": "object", "properties": {...}}
        ... )
    """

    success: bool = True
    agent: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "agent": "invoice-copilot",
                    "input_schema": {
                        "type": "object",
                        "properties": {"document_text": {"type": "string"}},
                        "required": ["document_text"],
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {"vendor": {"type": "string"}, "amount": {"type": "number"}},
                    },
                }
            ]
        }
    )


class InfoResponse(BaseModel):
    """
    Standard agent info endpoint response model.

    Attributes:
        success: Always True for success responses
        agent: Agent configuration details
        auth_enabled: Whether authentication is enabled
        version: Agent version
        metadata: Optional additional metadata

    Examples:
        >>> response = InfoResponse(
        ...     agent={"name": "invoice-copilot", "framework": "langgraph"},
        ...     auth_enabled=True,
        ...     version="1.0.0"
        ... )
    """

    success: bool = True
    agent: Dict[str, Any]
    auth_enabled: bool
    version: str
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "agent": {
                        "name": "invoice-copilot",
                        "description": "Extracts invoice data",
                        "framework": "langgraph",
                        "mode": "entrypoint",
                        "target": "app.graph:build_graph",
                    },
                    "auth_enabled": True,
                    "version": "1.0.0",
                    "metadata": {"author": "Acme Corp", "tags": ["invoice", "extraction"]},
                }
            ]
        }
    )
