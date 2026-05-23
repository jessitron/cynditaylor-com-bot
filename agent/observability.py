import os
import resource
import sys

from openinference.instrumentation.bedrock import BedrockInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agent.pricing import (
    AGENTCORE_CPU_USD_PER_HOUR,
    AGENTCORE_MEMORY_USD_PER_GB_HOUR,
    lookup as lookup_price,
)


_SESSION_ID: str | None = None


def get_session_id() -> str | None:
    return _SESSION_ID


class BedrockCostStampingProcessor(SpanProcessor):
    """Stamps cost.bedrock.* qty/price attributes on chat spans before export.

    Mutates span._attributes in on_end — this runs before the BatchSpanProcessor
    serializes the span, so attributes land in both local and cloud Honeycomb.
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


class AgentCoreCostStampingProcessor(SpanProcessor):
    """Stamps cost.agentcore.* attrs on agent.invocation spans.

    CPU is the delta of (utime+stime) between on_start and on_end — accurate
    per-invocation. Memory is ru_maxrss at on_end — the process high-water
    mark. ru_maxrss is monotonic per-process, so on a warm microVM serving
    many invocations, the first invocation establishes the baseline and
    later ones inherit it. That overcounts per-invocation memory cost
    slightly but matches the AgentCore billing model (allocated GB-hours,
    not used GB-hours). ru_maxrss is KB on Linux (where AgentCore runs),
    bytes on macOS — we detect at import.
    """

    _RU_MAXRSS_TO_BYTES = 1 if sys.platform == "darwin" else 1024

    _start_cpu: dict[int, float]

    def __init__(self) -> None:
        self._start_cpu = {}

    def on_start(self, span, parent_context=None):
        if span.name != "agent.invocation":
            return
        usage = resource.getrusage(resource.RUSAGE_SELF)
        self._start_cpu[span.context.span_id] = usage.ru_utime + usage.ru_stime

    def on_end(self, span: ReadableSpan) -> None:
        if span.name != "agent.invocation":
            return
        start = self._start_cpu.pop(span.context.span_id, None)
        if start is None:
            return
        usage = resource.getrusage(resource.RUSAGE_SELF)
        cpu_seconds = (usage.ru_utime + usage.ru_stime) - start
        peak_rss_bytes = usage.ru_maxrss * self._RU_MAXRSS_TO_BYTES
        new_attrs = {
            "cost.agentcore.cpu.seconds": cpu_seconds,
            "cost.agentcore.cpu.usd_per_hour": AGENTCORE_CPU_USD_PER_HOUR,
            "cost.agentcore.memory.peak_rss_bytes": peak_rss_bytes,
            "cost.agentcore.memory.usd_per_gb_hour": AGENTCORE_MEMORY_USD_PER_GB_HOUR,
        }
        if hasattr(span, "_attributes") and span._attributes is not None:
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
    provider.add_span_processor(AgentCoreCostStampingProcessor())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    trace.set_tracer_provider(provider)

    BedrockInstrumentor().instrument(tracer_provider=provider)
