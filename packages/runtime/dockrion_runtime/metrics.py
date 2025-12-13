"""
Prometheus Metrics for Dockrion Runtime

Provides standardized metrics for agent monitoring.
"""

from prometheus_client import Counter, Histogram, Gauge


class RuntimeMetrics:
    """
    Prometheus metrics for the runtime.
    
    Metrics:
        - dockrion_requests_total: Counter of requests by agent/endpoint/status
        - dockrion_request_latency_seconds: Histogram of request latency
        - dockrion_active_requests: Gauge of currently active requests
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize metrics with agent name as default label.
        
        Args:
            agent_name: Name of the agent (used as label)
        """
        self.agent_name = agent_name
        
        self.request_count = Counter(
            'dockrion_requests_total',
            'Total number of requests',
            ['agent', 'endpoint', 'status']
        )
        
        self.request_latency = Histogram(
            'dockrion_request_latency_seconds',
            'Request latency in seconds',
            ['agent', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.active_requests = Gauge(
            'dockrion_active_requests',
            'Number of active requests',
            ['agent']
        )
    
    def inc_request(self, endpoint: str, status: str) -> None:
        """Increment request counter."""
        self.request_count.labels(
            agent=self.agent_name,
            endpoint=endpoint,
            status=status
        ).inc()
    
    def observe_latency(self, endpoint: str, latency: float) -> None:
        """Record request latency."""
        self.request_latency.labels(
            agent=self.agent_name,
            endpoint=endpoint
        ).observe(latency)
    
    def inc_active(self) -> None:
        """Increment active request gauge."""
        self.active_requests.labels(agent=self.agent_name).inc()
    
    def dec_active(self) -> None:
        """Decrement active request gauge."""
        self.active_requests.labels(agent=self.agent_name).dec()

