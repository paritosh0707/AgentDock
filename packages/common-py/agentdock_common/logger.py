"""
AgentDock Application Logger

Structured logging for AgentDock services with support for correlation IDs,
context propagation, and JSON output for easy log aggregation.

This logger is for SERVICE-LEVEL logging (errors, debug, operations).
For AGENT-LEVEL telemetry (invocations, metrics), use the telemetry package.

Usage:
    from agentdock_common.logger import get_logger
    
    logger = get_logger("controller")
    logger.info("Service started", port=5001)
    
    # With request context
    logger = logger.with_context(request_id="abc-123")
    logger.info("Creating deployment", agent="invoice-copilot")
"""

import logging
import json
import sys
import time
from typing import Any, Dict, Optional
from contextvars import ContextVar
from datetime import datetime

from .constants import LOG_LEVELS


# Thread-safe context variable for request/correlation ID
_request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def set_request_id(request_id: str) -> None:
    """
    Set the request/correlation ID for the current context.
    
    This ID will be automatically included in all log messages within
    the same context (e.g., handling a single HTTP request).
    
    Args:
        request_id: Unique identifier for the request/operation
        
    Example:
        >>> set_request_id("req-abc-123")
        >>> logger.info("Processing request")  # Will include request_id
    """
    _request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """
    Get the current request/correlation ID from context.
    
    Returns:
        Request ID if set, None otherwise
    """
    return _request_id_var.get()


def clear_request_id() -> None:
    """Clear the request/correlation ID from current context"""
    _request_id_var.set(None)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs log records as JSON for easy parsing by log aggregation tools
    (ELK, Loki, CloudWatch, etc.)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "service": getattr(record, 'service_name', 'unknown'),
            "message": record.getMessage(),
        }
        
        # Add request/correlation ID if present
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add any extra context fields
        if hasattr(record, 'context'):
            log_data.update(record.context)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class AgentDockLogger:
    """
    Structured logger for AgentDock services.
    
    Provides consistent logging across all services with support for:
    - Structured logging (JSON output)
    - Correlation IDs for request tracing
    - Context propagation
    - Multiple log levels
    
    Attributes:
        service_name: Name of the service using this logger
        logger: Underlying Python logger instance
        context: Persistent context to include in all log messages
    """
    
    def __init__(self, service_name: str, log_level: str = "INFO"):
        """
        Initialize logger for a service.
        
        Args:
            service_name: Name of the service (e.g., "controller", "auth")
            log_level: Log level (DEBUG, INFO, WARN, ERROR)
        """
        self.service_name = service_name
        self.context: Dict[str, Any] = {}
        
        # Create underlying Python logger
        self.logger = logging.getLogger(f"agentdock.{service_name}")
        self.logger.setLevel(self._get_log_level(log_level))
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Add JSON formatter handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _get_log_level(self, level: str) -> int:
        """Convert log level string to logging constant"""
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        return level_map.get(level.lower(), logging.INFO)
    
    def _log(self, level: str, msg: str, **extra: Any) -> None:
        """
        Internal logging method.
        
        Args:
            level: Log level
            msg: Log message
            **extra: Additional context fields
        """
        # Combine persistent context with extra fields
        context = {**self.context, **extra}
        
        # Create log record with context
        log_method = getattr(self.logger, level.lower())
        log_method(
            msg,
            extra={
                'service_name': self.service_name,
                'context': context
            }
        )
    
    def debug(self, msg: str, **context: Any) -> None:
        """
        Log debug message.
        
        Args:
            msg: Debug message
            **context: Additional context fields
            
        Example:
            >>> logger.debug("Processing item", item_id="123", count=5)
        """
        self._log("debug", msg, **context)
    
    def info(self, msg: str, **context: Any) -> None:
        """
        Log info message.
        
        Args:
            msg: Info message
            **context: Additional context fields
            
        Example:
            >>> logger.info("Service started", port=5001, version="1.0.0")
        """
        self._log("info", msg, **context)
    
    def warning(self, msg: str, **context: Any) -> None:
        """
        Log warning message.
        
        Args:
            msg: Warning message
            **context: Additional context fields
            
        Example:
            >>> logger.warning("High memory usage", usage_mb=1024, threshold=512)
        """
        self._log("warning", msg, **context)
    
    def warn(self, msg: str, **context: Any) -> None:
        """Alias for warning()"""
        self.warning(msg, **context)
    
    def error(self, msg: str, **context: Any) -> None:
        """
        Log error message.
        
        Args:
            msg: Error message
            **context: Additional context fields
            
        Example:
            >>> logger.error("Database connection failed", error=str(e), host="localhost")
        """
        self._log("error", msg, **context)
    
    def critical(self, msg: str, **context: Any) -> None:
        """
        Log critical message.
        
        Args:
            msg: Critical message
            **context: Additional context fields
            
        Example:
            >>> logger.critical("Service shutdown", reason="Out of memory")
        """
        self._log("critical", msg, **context)
    
    def exception(self, msg: str, **context: Any) -> None:
        """
        Log exception with stack trace.
        
        Should be called from an exception handler to include stack trace.
        
        Args:
            msg: Error message
            **context: Additional context fields
            
        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     logger.exception("Operation failed", operation="risky")
        """
        # Combine persistent context with extra fields
        full_context = {**self.context, **context}
        
        self.logger.exception(
            msg,
            extra={
                'service_name': self.service_name,
                'context': full_context
            }
        )
    
    def with_context(self, **ctx: Any) -> 'AgentDockLogger':
        """
        Create a new logger with additional persistent context.
        
        Context is included in all subsequent log messages from the returned logger.
        Does not modify the original logger.
        
        Args:
            **ctx: Context fields to add
            
        Returns:
            New logger instance with combined context
            
        Example:
            >>> request_logger = logger.with_context(request_id="abc-123", user_id="user-456")
            >>> request_logger.info("Processing request")  # Includes request_id and user_id
            >>> request_logger.info("Request complete")    # Also includes both IDs
        """
        new_logger = AgentDockLogger(self.service_name)
        new_logger.context = {**self.context, **ctx}
        new_logger.logger = self.logger  # Share underlying logger
        return new_logger


def get_logger(service_name: str, log_level: str = "INFO") -> AgentDockLogger:
    """
    Create a logger for a service.
    
    Args:
        service_name: Name of the service (e.g., "controller", "auth")
        log_level: Log level (DEBUG, INFO, WARN, ERROR)
        
    Returns:
        AgentDockLogger instance
        
    Example:
        >>> logger = get_logger("controller")
        >>> logger.info("Service started", port=5001)
        
        >>> logger = get_logger("controller", log_level="DEBUG")
        >>> logger.debug("Detailed info", data={"key": "value"})
    """
    return AgentDockLogger(service_name, log_level)


def configure_logging(service_name: str, log_level: str = "INFO") -> AgentDockLogger:
    """
    Configure logging for a service and return logger.
    
    This is a convenience function that both configures logging and returns
    a logger instance.
    
    Args:
        service_name: Name of the service
        log_level: Log level (DEBUG, INFO, WARN, ERROR)
        
    Returns:
        Configured AgentDockLogger instance
        
    Example:
        >>> logger = configure_logging("controller", log_level="INFO")
        >>> logger.info("Service initialized")
    """
    return get_logger(service_name, log_level)

