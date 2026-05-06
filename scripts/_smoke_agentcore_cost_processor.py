"""Smoke the AgentCoreCostStampingProcessor in isolation.

Creates an agent.invocation span with a tiny CPU burn inside, then prints the
cost.agentcore.* attrs that landed on the span. No exporter — we read the
ReadableSpan handed to a tail-end SpanProcessor.
"""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider

from agent.observability import AgentCoreCostStampingProcessor


class _CapturingProcessor(SpanProcessor):
    captured: list[ReadableSpan]

    def __init__(self) -> None:
        self.captured = []

    def on_start(self, span, parent_context=None):
        return

    def on_end(self, span: ReadableSpan) -> None:
        self.captured.append(span)

    def shutdown(self) -> None:
        return

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def _burn_cpu(target_seconds: float) -> None:
    import time

    end = time.monotonic() + target_seconds
    x = 0
    while time.monotonic() < end:
        x = (x + 1) * 7 % 1_000_000
    print(f"  burned ~{target_seconds:.2f}s of CPU (sentinel x={x})")


def main() -> None:
    provider = TracerProvider(resource=Resource.create({}))
    provider.add_span_processor(AgentCoreCostStampingProcessor())
    capture = _CapturingProcessor()
    provider.add_span_processor(capture)
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer("smoke")
    with tracer.start_as_current_span("agent.invocation"):
        _burn_cpu(0.3)

    if not capture.captured:
        raise SystemExit("no span captured")
    span = capture.captured[0]
    attrs = dict(span.attributes or {})
    print()
    for key in sorted(attrs):
        if key.startswith("cost.agentcore."):
            print(f"  {key} = {attrs[key]}")

    required = {
        "cost.agentcore.cpu.seconds",
        "cost.agentcore.cpu.usd_per_hour",
        "cost.agentcore.memory.peak_rss_bytes",
        "cost.agentcore.memory.usd_per_gb_hour",
    }
    missing = required - attrs.keys()
    if missing:
        raise SystemExit(f"missing attrs: {missing}")
    if attrs["cost.agentcore.cpu.seconds"] <= 0:
        raise SystemExit("cpu.seconds must be > 0")
    if attrs["cost.agentcore.memory.peak_rss_bytes"] <= 0:
        raise SystemExit("peak_rss_bytes must be > 0")
    print("\nOK")


if __name__ == "__main__":
    main()
