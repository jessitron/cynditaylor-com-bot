import os

from openinference.instrumentation.bedrock import BedrockInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agent.pricing import lookup as lookup_price


_SESSION_ID: str | None = None


def get_session_id() -> str | None:
    return _SESSION_ID


class BedrockCostStampingProcessor(SpanProcessor):
    """Stamps cost.bedrock.* qty/price attributes on chat spans before export.

    Mutates span._attributes in on_end — this runs before the BatchSpanProcessor
    serializes the span, so attributes land in both Phoenix and Honeycomb.
    """

    _CHAT_SPAN_NAMES = {"chat", "Model invoke"}

    def on_start(self, span, parent_context=None):
        return

    def on_end(self, span: ReadableSpan) -> None:
        if span.name not in self._CHAT_SPAN_NAMES:
            return
        attrs = span.attributes or {}
        model_id = attrs.get("gen_ai.request.model")
        prices = lookup_price(model_id)
        if not prices:
            return

        # input_tokens here is the *uncached* input — Bedrock returns
        # inputTokens, cacheReadInputTokens, cacheWriteInputTokens as three
        # independent buckets, so they multiply against three different prices.
        buckets = {
            "input": ("gen_ai.usage.input_tokens", prices["input"]),
            "output": ("gen_ai.usage.output_tokens", prices["output"]),
            "cache_read": (
                "gen_ai.usage.cache_read_input_tokens",
                prices["cache_read"],
            ),
            "cache_write": (
                "gen_ai.usage.cache_write_input_tokens",
                prices["cache_write"],
            ),
        }

        new_attrs: dict = {}
        for label, (token_attr, price) in buckets.items():
            qty = attrs.get(token_attr)
            if qty is None:
                continue
            new_attrs[f"cost.bedrock.{label}.qty"] = int(qty)
            new_attrs[f"cost.bedrock.{label}.price"] = price

        if new_attrs and hasattr(span, "_attributes") and span._attributes is not None:
            span._attributes.update(new_attrs)

    def shutdown(self) -> None:
        return

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def configure_tracing(
    session_id: str | None = None,
    email_from: str | None = None,
) -> None:
    global _SESSION_ID
    _SESSION_ID = session_id
    resource_attrs = {"openinference.project.name": os.environ["OTEL_SERVICE_NAME"]}
    if session_id:
        resource_attrs["session.id"] = session_id
        resource_attrs["email.thread.id"] = session_id
    if email_from:
        resource_attrs["email.from"] = email_from
    resource = Resource.create(resource_attrs)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BedrockCostStampingProcessor())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    trace.set_tracer_provider(provider)

    BedrockInstrumentor().instrument(tracer_provider=provider)
