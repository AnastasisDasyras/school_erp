from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# HTTP metrics — populated by PrometheusMiddleware in main.py
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

# Cache metrics — incremented in cache_aside.py
cache_hits_total = Counter("cache_hits_total", "Redis cache hits", ["key_prefix"])
cache_misses_total = Counter("cache_misses_total", "Redis cache misses", ["key_prefix"])

# Outbox metrics — updated by the relay
outbox_pending_events = Gauge("outbox_pending_events", "Outbox events waiting to be published")
outbox_published_total = Counter("outbox_published_total", "Outbox events successfully published")
outbox_failed_total = Counter("outbox_failed_total", "Outbox events that failed to publish")

# DB pool metrics — updated on each session checkout
db_pool_checked_out = Gauge("db_pool_checked_out", "SQLAlchemy pool connections in use")
