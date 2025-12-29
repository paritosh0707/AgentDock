"""Tests for the telemetry package."""


class TestTelemetryImports:
    """Test that telemetry modules can be imported."""

    def test_import_prometheus_utils(self):
        """Test importing prometheus_utils module."""
        from dockrion_telemetry import prometheus_utils

        assert prometheus_utils is not None

    def test_import_logger(self):
        """Test importing logger module."""
        from dockrion_telemetry import logger

        assert logger is not None


class TestPrometheusMetrics:
    """Test prometheus metrics utilities."""

    def test_metrics_module_has_counter(self):
        """Test that we can create a counter."""
        from prometheus_client import Counter

        test_counter = Counter("test_counter_total", "Test counter for testing")
        assert test_counter is not None

    def test_metrics_module_has_histogram(self):
        """Test that we can create a histogram."""
        from prometheus_client import Histogram

        test_histogram = Histogram("test_histogram_seconds", "Test histogram for testing")
        assert test_histogram is not None
