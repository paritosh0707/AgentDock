"""
dockrion HTTP Response Models

This module provides standard response models for consistent API responses across
all dockrion services.

Usage:
    from dockrion_common.http_models import error_response, invoke_response
    
    return invoke_response(output=result, metadata={"agent": "my-agent"})
    return error_response(ValidationError("Invalid input"))
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from .errors import DockrionError


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
                    "code": "VALIDATION_ERROR"
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
                    "items": [
                        {"id": "1", "name": "agent-1"},
                        {"id": "2", "name": "agent-2"}
                    ],
                    "total": 25,
                    "page": 1,
                    "page_size": 10
                }
            ]
        }
    )


def error_response(error: Exception) -> dict:
    """
    Create a standard error response dictionary from an exception.
    
    Handles both DockrionError (with code) and generic exceptions.
    
    Args:
        error: Exception to convert to error response
        
    Returns:
        Dictionary with success=False, error message, and code
        
    Examples:
        >>> from dockrion_common.errors import ValidationError
        >>> error_response(ValidationError("Invalid input"))
        {'success': False, 'error': 'Invalid input', 'code': 'VALIDATION_ERROR'}
        
        >>> error_response(ValueError("Something went wrong"))
        {'success': False, 'error': 'Something went wrong', 'code': 'INTERNAL_ERROR'}
    """
    if isinstance(error, DockrionError):
        return ErrorResponse(
            error=error.message,
            code=error.code
        ).model_dump()
    else:
        return ErrorResponse(
            error=str(error),
            code="INTERNAL_ERROR"
        ).model_dump()


def paginated_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int
) -> dict:
    """
    Create a standard paginated response dictionary.
    
    Args:
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Dictionary with pagination metadata
        
    Examples:
        >>> paginated_response(
        ...     items=[{"id": "1"}, {"id": "2"}],
        ...     total=100,
        ...     page=1,
        ...     page_size=10
        ... )
        {'success': True, 'items': [...], 'total': 100, 'page': 1, 'page_size': 10}
    """
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    ).model_dump()


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
        >>> response = HealthResponse(
        ...     status="ok",
        ...     service="controller",
        ...     version="1.0.0",
        ...     timestamp=1699456789.123
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
                    "timestamp": 1699456789.123
                },
                {
                    "status": "ok",
                    "service": "runtime:invoice-copilot",
                    "version": "1.0.0",
                    "timestamp": 1699456789.123,
                    "agent": "invoice-copilot",
                    "framework": "langgraph"
                }
            ]
        }
    )


def health_response(
    service: str,
    version: str,
    status: str = "ok",
    agent: Optional[str] = None,
    framework: Optional[str] = None
) -> dict:
    """
    Create a standard health check response.
    
    Args:
        service: Service name
        version: Service version
        status: Health status (default: "ok")
        agent: Optional agent name (for runtime health checks)
        framework: Optional agent framework (for runtime health checks)
        
    Returns:
        Dictionary with health check data
        
    Examples:
        >>> import time
        >>> health_response("controller", "1.0.0")
        {'status': 'ok', 'service': 'controller', 'version': '1.0.0', 'timestamp': ...}
        >>> health_response("runtime:invoice-copilot", "1.0.0", agent="invoice-copilot", framework="langgraph")
        {'status': 'ok', 'service': '...', 'version': '1.0.0', 'timestamp': ..., 'agent': '...', 'framework': '...'}
    """
    import time
    return HealthResponse(
        status=status,
        service=service,
        version=version,
        timestamp=time.time(),
        agent=agent,
        framework=framework
    ).model_dump(exclude_none=True)


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
                    "output": {
                        "vendor": "Acme Corp",
                        "amount": 1500.00,
                        "currency": "USD"
                    },
                    "metadata": {
                        "agent": "invoice-copilot",
                        "framework": "langgraph",
                        "latency_seconds": 0.523
                    }
                }
            ]
        }
    )


def invoke_response(output: Any, metadata: Dict[str, Any]) -> dict:
    """
    Create a standard agent invocation response dictionary.
    
    Args:
        output: Agent output (any JSON-serializable type)
        metadata: Invocation metadata dictionary
        
    Returns:
        Dictionary with success=True, output, and metadata
        
    Examples:
        >>> invoke_response(
        ...     output={"vendor": "Acme Corp"},
        ...     metadata={"agent": "invoice-copilot", "latency_seconds": 0.5}
        ... )
        {'success': True, 'output': {'vendor': 'Acme Corp'}, 'metadata': {...}}
    """
    return InvokeResponse(output=output, metadata=metadata).model_dump()


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
            "examples": [
                {
                    "success": True,
                    "status": "ready",
                    "agent": "invoice-copilot"
                }
            ]
        }
    )


def ready_response(agent: str, status: str = "ready") -> dict:
    """
    Create a standard readiness check response.
    
    Args:
        agent: Agent name
        status: Readiness status (default: "ready")
        
    Returns:
        Dictionary with success=True, status, and agent
        
    Examples:
        >>> ready_response("invoice-copilot")
        {'success': True, 'status': 'ready', 'agent': 'invoice-copilot'}
    """
    return ReadyResponse(status=status, agent=agent).model_dump()


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
                        "properties": {
                            "document_text": {"type": "string"}
                        },
                        "required": ["document_text"]
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "vendor": {"type": "string"},
                            "amount": {"type": "number"}
                        }
                    }
                }
            ]
        }
    )


def schema_response(
    agent: str,
    input_schema: Dict[str, Any],
    output_schema: Dict[str, Any]
) -> dict:
    """
    Create a standard schema endpoint response.
    
    Args:
        agent: Agent name
        input_schema: Input JSON schema definition
        output_schema: Output JSON schema definition
        
    Returns:
        Dictionary with success=True and schema information
        
    Examples:
        >>> schema_response(
        ...     agent="invoice-copilot",
        ...     input_schema={"type": "object"},
        ...     output_schema={"type": "object"}
        ... )
        {'success': True, 'agent': '...', 'input_schema': {...}, 'output_schema': {...}}
    """
    return SchemaResponse(
        agent=agent,
        input_schema=input_schema,
        output_schema=output_schema
    ).model_dump()


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
                        "target": "app.graph:build_graph"
                    },
                    "auth_enabled": True,
                    "version": "1.0.0",
                    "metadata": {
                        "author": "Acme Corp",
                        "tags": ["invoice", "extraction"]
                    }
                }
            ]
        }
    )


def info_response(
    agent: Dict[str, Any],
    auth_enabled: bool,
    version: str,
    metadata: Optional[Dict[str, Any]] = None
) -> dict:
    """
    Create a standard agent info response.
    
    Args:
        agent: Agent configuration dictionary
        auth_enabled: Whether authentication is enabled
        version: Agent version
        metadata: Optional additional metadata
        
    Returns:
        Dictionary with success=True and agent information
        
    Examples:
        >>> info_response(
        ...     agent={"name": "invoice-copilot", "framework": "langgraph"},
        ...     auth_enabled=True,
        ...     version="1.0.0"
        ... )
        {'success': True, 'agent': {...}, 'auth_enabled': True, 'version': '1.0.0'}
    """
    return InfoResponse(
        agent=agent,
        auth_enabled=auth_enabled,
        version=version,
        metadata=metadata
    ).model_dump(exclude_none=True)

