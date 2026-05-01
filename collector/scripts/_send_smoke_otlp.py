"""Send a synthetic span with a span-event to the collector and assert export succeeded.

Used by collector/scripts/smoke. The intent of the payload is to exercise the
transform pipeline: a span event with attributes that the collector should
hoist onto the parent span and then drop the now-empty event.
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
        resource=Resource.create({"service.name": "collector-smoke"})
    )
    provider.add_span_processor(SimpleSpanProcessor(mem))

    tracer = provider.get_tracer("smoke")
    marker = secrets.token_hex(8)
    with tracer.start_as_current_span("collector-smoke-test") as span:
        span.add_event(
            "smoke.test.event",
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
            "OTLP export FAILED. Check the collector's CloudWatch log group "
            "/aws/lambda/<COLLECTOR_NAME> for details."
        )

    print(f"trace_id:    {ctx.trace_id:032x}")
    print(f"span_id:     {ctx.span_id:016x}")
    print(f"marker:      {marker}")
    print()
    print("export succeeded. In Honeycomb (service=collector-smoke), expect:")
    print("  - one span 'collector-smoke-test'")
    print("  - span attrs include smoke.lifted_attr, smoke.marker")
    print("  - NO separate row with name='smoke.test.event' (filter dropped it)")


if __name__ == "__main__":
    main()
