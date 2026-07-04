# 0010 — Observability: Tracing, Metrics, and Logs

## Status
Accepted

## Context
Phases 0–5 gave us a running distributed system — 2 backend replicas, an
outbox relay, and 2 microservices all communicating via SNS/SQS. Without
observability, debugging a slow request means grepping logs across five
containers with no shared timestamp or request context. Phase 6 answers the
question every interviewer asks: **"How would you debug a slow request in
production?"**

The observability triad answers three different questions:
- **Traces** — "What happened to *this specific request*?" (request-scoped)
- **Metrics** — "How is the system performing *overall*?" (aggregate, time-series)
- **Logs** — "What did the code say when it ran?" (event-level detail)

All three are needed. Metrics tell you *something is wrong*; traces tell you
*where*; logs tell you *why*.

## Decision

### Traces — OpenTelemetry → Jaeger

We use **OpenTelemetry** (OTel) as the instrumentation standard, not a
vendor-specific SDK. This is the correct choice because OTel is now the
industry standard: the same instrumentation code works with Jaeger locally
and with AWS X-Ray, Datadog, Honeycomb, or any other OTLP-compatible backend
in production — *zero code change*, only a different exporter endpoint.

**`opentelemetry-instrumentation-fastapi`** auto-instruments every HTTP
handler: it creates a span for each request, records the route, method,
status code, and duration automatically. We don't have to manually wrap
every route.

**`opentelemetry-instrumentation-sqlalchemy`** auto-instruments the
SQLAlchemy engine: every SQL query becomes a child span under the
request span. In Jaeger you can see the exact query, its duration, and
whether it ran inside a transaction.

**Both microservices** create a manual span per SQS message
(`tracer.start_as_current_span("notification.process AttendanceRecorded")`).
This gives us a full cross-service trace: the Jaeger UI shows the API
request span, its DB child spans, and separately the consumer spans that
processed the resulting event — the complete picture of what one attendance
POST caused across the system.

The OTel SDK is configured via environment variables (`OTEL_SERVICE_NAME`,
`OTEL_EXPORTER_OTLP_ENDPOINT`) injected by docker-compose. Without them
(unit tests, bare local dev) we fall back to `ConsoleSpanExporter` so the
app still boots without error.

### Metrics — Prometheus + Grafana

**Prometheus** scrapes a `/metrics` endpoint on both backend replicas every
15s. We expose metrics via `prometheus-client` (the official Python library),
not OTel metrics, because the OTel metrics API is still less mature than
OTel tracing in the Python ecosystem and `prometheus-client` is the
de-facto standard for Python services.

Four metric categories:

1. **HTTP metrics** (`http_requests_total`, `http_request_duration_seconds`)
   populated by `PrometheusMiddleware`. The middleware uses the **route
   pattern** (`/api/v1/students/{student_id}`) not the concrete path
   (`/api/v1/students/ae5a8aa9-...`) as the label. This is critical:
   using concrete paths would create a new label combination for every
   unique ID — Prometheus cardinality would explode and memory usage
   would grow unboundedly.

2. **Cache metrics** (`cache_hits_total`, `cache_misses_total`) incremented
   in `cache_aside.py`. The Grafana panel computes
   `hits / (hits + misses)` as the cache hit ratio — the key SRE signal
   for whether the cache is doing its job.

3. **Outbox metrics** (`outbox_pending_events`, `outbox_published_total`,
   `outbox_failed_total`) updated by the relay. A rising
   `outbox_pending_events` gauge means the relay is falling behind — an
   alert on this catches publish failures before they cause noticeable
   downstream lag.

4. **DB pool** (`db_pool_checked_out`) to detect connection exhaustion
   before it causes 503s.

**Grafana** is pre-provisioned with a Prometheus datasource, a Loki
datasource, and a Jaeger datasource via the `provisioning/` mount — no
manual UI setup required after `docker compose up`. The starter dashboard
covers request rate, P99 latency, error rate, and cache hit ratio.

### Logs — Loki + Promtail

Structured JSON logs were already in place from Phase 0 (structlog).
**Promtail** ships Docker container logs to **Loki** by reading
`/var/lib/docker/containers/*/*-json.log`, tagging each line with the
container name. Loki is available in Grafana as a datasource, so you can:

1. Open a slow trace in Jaeger.
2. Copy the timestamp.
3. Switch to Grafana Explore, filter by `container_name="backend1"`, and
   see the exact log lines from that moment.

This "jump from trace to log" workflow is the concrete answer to
"how would you debug a production issue?" in an interview.

## Consequences

- **Jaeger UI** at `localhost:16686` — search by service name, see all
  spans for a request, drill into SQL queries.
- **Prometheus** at `localhost:9090` — raw metric explorer.
- **Grafana** at `localhost:3000` (admin/admin) — dashboards + Loki log
  exploration. Pre-provisioned datasources and a starter dashboard on
  `docker compose up`.
- **No vendor lock-in**: switching from local Jaeger to AWS X-Ray in
  production requires changing `OTEL_EXPORTER_OTLP_ENDPOINT` and
  installing the X-Ray OTLP exporter — the instrumentation code is
  identical.
- **Cardinality discipline**: the route-pattern label strategy in
  `PrometheusMiddleware` is a production requirement, not a nicety.
  Teams that skip this end up with OOM-killed Prometheus instances.
- **The microservice consumer spans are not connected to the originating
  HTTP trace** — OTel trace context propagation across SQS is not wired
  here (it would require injecting W3C traceparent headers into the SNS
  message attributes and extracting them in the consumers). This is a
  known gap; adding it is a one-day task but is left as a Phase 8
  enhancement to keep this phase focused.
