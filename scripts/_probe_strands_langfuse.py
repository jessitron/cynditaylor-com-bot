"""Probe whether Strands' tracer detects langfuse + latest semconv with current env."""

import os

print("env inputs:")
for var in (
    "OTEL_SEMCONV_STABILITY_OPT_IN",
    "LANGFUSE_BASE_URL",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
):
    print(f"  {var}={os.environ.get(var, '<unset>')}")
print()

from strands.telemetry.tracer import Tracer

t = Tracer()
print(f"Tracer.use_latest_genai_conventions = {t.use_latest_genai_conventions}")
print(f"Tracer.is_langfuse = {t.is_langfuse}")
