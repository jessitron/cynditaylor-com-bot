"""Send a synthetic span with a gen_ai-style span-event to the local collector.

Mirrors collector/scripts/_send_smoke_otlp.py — the local collector enforces
the same bearer auth as cloud (different token). The span event the
collector should hoist onto the parent span via the OTTL transform.
"""

import argparse
import secrets
import sys

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--token", required=True)
    args = ap.parse_args()

    mem = InMemorySpanExporter()
    provider = TracerProvider(
        resource=Resource.create({"service.name": "local-collector-smoke"})
    )
    provider.add_span_processor(SimpleSpanProcessor(mem))

    tracer = provider.get_tracer("smoke")
    marker = secrets.token_hex(8)
    with tracer.start_as_current_span("local-collector-smoke-test") as span:
        span.add_event(
            "gen_ai.client.inference.operation.details",
            attributes={
                "smoke.lifted_attr": "lifted",
                "smoke.marker": marker,
            },
        )
        ctx = span.get_span_context()

    spans = mem.get_finished_spans()
    if not spans:
        sys.exit("no span captured — internal error")

    exporter = OTLPSpanExporter(
        endpoint=args.endpoint,
        headers={"authorization": f"Bearer {args.token}"},
    )
    result = exporter.export(spans)

    if result != SpanExportResult.SUCCESS:
        sys.exit(
            "OTLP export FAILED. Check `docker logs cynditaylor-collector` for details."
        )

    print(f"trace_id: {ctx.trace_id:032x}")
    print(f"marker:   {marker}")
    print()
    print('In Honeycomb "local" env (service=local-collector-smoke), expect:')
    print("  - one span 'local-collector-smoke-test'")
    print("  - span attrs include smoke.lifted_attr, smoke.marker")
    print("  - collector.boswell=washere, collector.boswell.version=<git short-sha>")
