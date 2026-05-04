import os

from openinference.instrumentation.bedrock import BedrockInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


_SESSION_ID: str | None = None


def get_session_id() -> str | None:
    return _SESSION_ID


def configure_tracing(session_id: str | None = None) -> None:
    global _SESSION_ID
    _SESSION_ID = session_id
    resource_attrs = {"openinference.project.name": os.environ["OTEL_SERVICE_NAME"]}
    if session_id:
        resource_attrs["session.id"] = session_id
    resource = Resource.create(resource_attrs)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    trace.set_tracer_provider(provider)

    BedrockInstrumentor().instrument(tracer_provider=provider)
