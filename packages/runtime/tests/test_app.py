"""Tests for the runtime app module."""


class TestRuntimeImports:
    """Test that runtime modules can be imported."""

    def test_import_dockrion_runtime(self):
        """Test importing dockrion_runtime package."""
        import dockrion_runtime

        assert dockrion_runtime is not None

    def test_import_app_module(self):
        """Test importing app module."""
        from dockrion_runtime import app

        assert app is not None

    def test_import_config_module(self):
        """Test importing config module."""
        from dockrion_runtime import config

        assert config is not None

    def test_import_metrics_module(self):
        """Test importing metrics module."""
        from dockrion_runtime import metrics

        assert metrics is not None


class TestRuntimeConfig:
    """Test runtime configuration."""

    def test_config_defaults(self):
        """Test that config has sensible defaults."""
        from dockrion_runtime.config import RuntimeConfig

        config = RuntimeConfig(agent_name="test-agent", agent_framework="langgraph")
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.agent_name == "test-agent"
        assert config.agent_framework == "langgraph"


class TestHealthEndpoint:
    """Test health endpoint."""

    def test_health_endpoint_exists(self):
        """Test that health endpoint module exists."""
        from dockrion_runtime.endpoints import health

        assert health is not None


class TestEventsPackageDetection:
    """Test events package availability detection."""

    def test_events_package_flag_exists(self):
        """Test that _EVENTS_PACKAGE_AVAILABLE flag exists in app module."""
        from dockrion_runtime.app import _EVENTS_PACKAGE_AVAILABLE

        # Should be True since dockrion_events is installed in this workspace
        assert isinstance(_EVENTS_PACKAGE_AVAILABLE, bool)
        assert _EVENTS_PACKAGE_AVAILABLE is True

    def test_runs_router_not_registered_without_events_flag(self):
        """Verify runs router registration depends on events package availability."""
        import inspect

        from dockrion_runtime.app import create_app

        # Check the source code contains the guard condition
        source = inspect.getsource(create_app)

        # Should check _EVENTS_PACKAGE_AVAILABLE before registering runs router
        assert "_EVENTS_PACKAGE_AVAILABLE" in source
        assert "if config.enable_async_runs:" in source
        assert "if _EVENTS_PACKAGE_AVAILABLE:" in source
