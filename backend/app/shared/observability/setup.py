from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_tracing(app: object, engine: object | None = None) -> None:
    """Configure OpenTelemetry tracing for the FastAPI monolith.

    When OTEL_EXPORTER_OTLP_ENDPOINT is set (injected via docker-compose),
    spans go to Jaeger over gRPC. Without it (unit tests, local dev without
    Docker) we fall back to a no-op console exporter so the app still boots.

    Called once at startup in main.py before any request can arrive.
    """
    service_name = os.getenv("OTEL_SERVICE_NAME", "school-erp-backend")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]

    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine)
