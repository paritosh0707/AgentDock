"""
dockrion HTTP Response Models

This module provides standard response models for consistent API responses across
all dockrion services.

Usage:
    from dockrion_common.http_models import success_response, error_response
    
    return success_response({"id": "123", "status": "running"})
    return error_response(ValidationError("Invalid input"))
"""

from typing import Any, List
from pydantic import BaseModel, ConfigDict

from .errors import DockrionError


class APIResponse(BaseModel):
    """
    Standard success response model.
    
    Attributes:
        success: Always True for success responses
        data: Response payload (any type)
        
    Examples:
        >>> response = APIResponse(data={"id": "123", "status": "running"})
        >>> response.model_dump()
        {'success': True, 'data': {'id': '123', 'status': 'running'}}
    """
    success: bool = True
    data: Any
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "data": {
                        "id": "dep-123",
                        "agent": "invoice-copilot",
                        "status": "running"
                    }
                }
            ]
        }
    )


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


def success_response(data: Any) -> dict:
    """
    Create a standard success response dictionary.
    
    Args:
        data: Response payload (any JSON-serializable type)
        
    Returns:
        Dictionary with success=True and data
        
    Examples:
        >>> success_response({"id": "123", "status": "running"})
        {'success': True, 'data': {'id': '123', 'status': 'running'}}
        
        >>> success_response([1, 2, 3])
        {'success': True, 'data': [1, 2, 3]}
    """
    return APIResponse(data=data).model_dump()


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
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "service": "controller",
                    "version": "1.0.0",
                    "timestamp": 1699456789.123
                }
            ]
        }
    )


def health_response(service: str, version: str, status: str = "ok") -> dict:
    """
    Create a standard health check response.
    
    Args:
        service: Service name
        version: Service version
        status: Health status (default: "ok")
        
    Returns:
        Dictionary with health check data
        
    Examples:
        >>> import time
        >>> health_response("controller", "1.0.0")
        {'status': 'ok', 'service': 'controller', 'version': '1.0.0', 'timestamp': ...}
    """
    import time
    return HealthResponse(
        status=status,
        service=service,
        version=version,
        timestamp=time.time()
    ).model_dump()

