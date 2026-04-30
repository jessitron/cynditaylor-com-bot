import os

from openinference.instrumentation.bedrock import BedrockInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing() -> None:
    resource = Resource.create(
        {"openinference.project.name": os.environ["OTEL_SERVICE_NAME"]}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    trace.set_tracer_provider(provider)

    BedrockInstrumentor().instrument(tracer_provider=provider)
