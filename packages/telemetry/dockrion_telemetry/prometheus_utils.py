from prometheus_client import Counter, Histogram

REQ_COUNT = Counter("dockrion_requests_total", "Total requests", ["agent", "version"])
LATENCY = Histogram("dockrion_latency_seconds", "Latency seconds", ["agent", "version"])


def observe_request(agent: str, version: str, latency_s: float):
    REQ_COUNT.labels(agent, version).inc()
    LATENCY.labels(agent, version).observe(latency_s)
