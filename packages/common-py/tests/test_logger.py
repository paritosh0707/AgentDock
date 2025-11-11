"""
Tests for the logger module
"""

import json
import pytest
from io import StringIO
from agentdock_common.logger import (
    get_logger,
    configure_logging,
    set_request_id,
    get_request_id,
    clear_request_id,
)


class TestLogger:
    """Test AgentDockLogger"""
    
    def test_get_logger(self):
        """Test get_logger creates a logger"""
        logger = get_logger("test-service")
        assert logger.service_name == "test-service"
        assert logger.context == {}
    
    def test_logger_with_log_level(self):
        """Test logger with custom log level"""
        logger = get_logger("test-service", log_level="DEBUG")
        assert logger.service_name == "test-service"
    
    def test_logger_info(self, caplog):
        """Test info logging"""
        logger = get_logger("test-service")
        logger.info("Test message", key="value")
        # Logger outputs JSON to stdout, not caplog
        # Just verify no exceptions
    
    def test_logger_error(self):
        """Test error logging"""
        logger = get_logger("test-service")
        logger.error("Error message", error="test error")
        # Just verify no exceptions
    
    def test_logger_debug(self):
        """Test debug logging"""
        logger = get_logger("test-service", log_level="DEBUG")
        logger.debug("Debug message", data={"key": "value"})
        # Just verify no exceptions
    
    def test_logger_warning(self):
        """Test warning logging"""
        logger = get_logger("test-service")
        logger.warning("Warning message", reason="test")
        logger.warn("Warn message", reason="test")  # Test alias
        # Just verify no exceptions
    
    def test_logger_critical(self):
        """Test critical logging"""
        logger = get_logger("test-service")
        logger.critical("Critical message", severity="high")
        # Just verify no exceptions
    
    def test_logger_with_context(self):
        """Test logger with context"""
        logger = get_logger("test-service")
        logger_with_ctx = logger.with_context(request_id="req-123", user_id="user-456")
        
        # Context is added
        assert "request_id" in logger_with_ctx.context
        assert logger_with_ctx.context["request_id"] == "req-123"
        assert logger_with_ctx.context["user_id"] == "user-456"
        
        # Original logger unchanged
        assert logger.context == {}
    
    def test_logger_context_chaining(self):
        """Test chaining context"""
        logger = get_logger("test-service")
        logger1 = logger.with_context(key1="value1")
        logger2 = logger1.with_context(key2="value2")
        
        assert logger1.context == {"key1": "value1"}
        assert logger2.context == {"key1": "value1", "key2": "value2"}
        assert logger.context == {}
    
    def test_configure_logging(self):
        """Test configure_logging"""
        logger = configure_logging("test-service", log_level="INFO")
        assert logger.service_name == "test-service"


class TestRequestID:
    """Test request ID context management"""
    
    def test_set_request_id(self):
        """Test setting request ID"""
        set_request_id("req-abc-123")
        assert get_request_id() == "req-abc-123"
        clear_request_id()
    
    def test_get_request_id_none(self):
        """Test getting request ID when not set"""
        clear_request_id()
        assert get_request_id() is None
    
    def test_clear_request_id(self):
        """Test clearing request ID"""
        set_request_id("req-xyz-789")
        assert get_request_id() == "req-xyz-789"
        clear_request_id()
        assert get_request_id() is None
    
    def test_request_id_isolation(self):
        """Test request ID is isolated per context"""
        set_request_id("req-first")
        assert get_request_id() == "req-first"
        
        set_request_id("req-second")
        assert get_request_id() == "req-second"
        
        clear_request_id()


class TestLoggerIntegration:
    """Integration tests for logger"""
    
    def test_logger_end_to_end(self):
        """Test complete logging flow"""
        # Create logger
        logger = get_logger("controller", log_level="INFO")
        
        # Set request ID
        set_request_id("req-integration-test")
        
        # Log with context
        logger = logger.with_context(deployment_id="dep-123")
        logger.info("Creating deployment", agent="test-agent")
        logger.error("Deployment failed", error="timeout")
        
        # Clear request ID
        clear_request_id()
        
        # Just verify no exceptions
        assert True
    
    def test_logger_exception_handling(self):
        """Test exception logging"""
        logger = get_logger("test-service")
        
        try:
            raise ValueError("Test error")
        except Exception:
            logger.exception("Caught exception", operation="test")
        
        # Just verify no exceptions in logging
        assert True

