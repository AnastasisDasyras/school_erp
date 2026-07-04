from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_tracing() -> None:
    """Configure OTel tracing for the notification microservice.

    When OTEL_EXPORTER_OTLP_ENDPOINT is set (injected by docker-compose),
    spans are exported to Jaeger. Otherwise falls back to ConsoleSpanExporter
    so local dev without Docker still works without error.
    """
    service_name = os.getenv("OTEL_SERVICE_NAME", "notification")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True) if otlp_endpoint else ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer("notification")
