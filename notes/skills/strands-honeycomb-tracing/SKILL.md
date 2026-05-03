---
name: strands-honeycomb-tracing
description: Configure a Strands Agents (Python) application to ship OpenTelemetry traces to Honeycomb in a way Honeycomb's UI can actually read — individual queryable columns for gen_ai.usage.*, gen_ai.server.*, and conversation messages on the spans (not buried inside JSON blobs or stuck on span events). Use when setting up tracing for a new Strands app, when an existing Strands+Honeycomb integration shows messages missing from the AI view, when token/latency fields show up as one big `metadata` JSON string instead of separate columns, or when the trigger words "Strands tracing", "Strands telemetry", "Strands Honeycomb", "gen_ai semconv", or "Honeycomb AI view" appear.
---

Set up Strands Agent tracing so Honeycomb's column-oriented backend and AI view get the data they need. There are three traps in the default setup; this skill walks past all three.

## The traps

1. **`StrandsAgentsToOpenInferenceProcessor`** (from the `openinference-instrumentation-strands-agents` PyPI package) sweeps any `gen_ai.*` attribute it didn't translate into a single JSON-encoded `metadata` string column. Phoenix renders that as a key-value table; Honeycomb sees one opaque string and can't `P99(gen_ai.server.time_to_first_token)`.
2. **The default Strands GenAI semconv emits per-message span events** (`gen_ai.user.message`, `gen_ai.assistant.message`, etc.) rather than the newer `gen_ai.input.messages` / `gen_ai.output.messages` arrays. Honeycomb's AI view queries the latter shape.
3. **Even with the latest semconv enabled, Strands writes those message arrays as span EVENT attributes, not span attributes.** Honeycomb's columnar UI queries span attributes. Strands gates the "also copy to span attributes" behavior on a `is_langfuse` heuristic — substring `"langfuse"` in `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, or `LANGFUSE_BASE_URL`. Honeycomb endpoints don't trip it; we set `LANGFUSE_BASE_URL` to a stub value containing the substring `"langfuse"` to flip the switch.

## Setup

### 1. Dependencies

Use only `strands-agents` plus the OTLP HTTP exporter. Do **not** install `openinference-instrumentation-strands-agents`. `openinference-instrumentation-bedrock` is fine to keep if you're on Bedrock — it writes vanilla OpenInference `llm.*` attrs on `bedrock.converse_stream` spans, which complement (don't conflict with) Strands' `gen_ai.*`.

```toml
[project]
dependencies = [
    "strands-agents>=0.1.0",
    "opentelemetry-sdk>=1.27.0",
    "opentelemetry-exporter-otlp-proto-http>=1.27.0",
    # Optional: vanilla OpenInference attrs on bedrock spans.
    "openinference-instrumentation-bedrock>=0.1.0",
]
```

### 2. Tracing configuration (Python)

```python
import os

from openinference.instrumentation.bedrock import BedrockInstrumentor  # optional
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing() -> None:
    resource = Resource.create({"service.name": os.environ["OTEL_SERVICE_NAME"]})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    BedrockInstrumentor().instrument(tracer_provider=provider)  # optional
```

That's it. **No** `StrandsAgentsToOpenInferenceProcessor`. Strands' built-in OTel instrumentation handles the rest.

### 3. Environment variables

These three are the load-bearing ones for getting Honeycomb's UI happy:

```bash
# Standard OTLP -> Honeycomb
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://api.honeycomb.io/v1/traces
OTEL_EXPORTER_OTLP_HEADERS=x-honeycomb-team=<INGEST_KEY>
OTEL_SERVICE_NAME=<your-service-name>

# Trap 2: emit gen_ai.input.messages / gen_ai.output.messages as JSON arrays
# instead of separate per-message span events.
OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental

# Trap 3: trip Strands' is_langfuse heuristic so those JSON arrays land on
# span attributes (Honeycomb-queryable) in addition to span events.
# The literal substring "langfuse" is what matters; the rest is documentation.
# *** Skip this if you're solving trap 3 in a collector — see next section. ***
LANGFUSE_BASE_URL=langfuse-stub-for-honeycomb
```

Optional but useful:

```bash
# Adds full tool JSON schemas to LLM-call spans (gen_ai.tool.json_schema).
# Append to the existing OTEL_SEMCONV_STABILITY_OPT_IN list, comma-separated.
OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental,gen_ai_tool_definitions
```

### 4. Alternative: solve trap 3 in a collector instead of via `LANGFUSE_BASE_URL`

If you already have (or want) an OTel Collector in your pipeline, do the event-to-attribute lift there. The producer then stays standards-compliant (vanilla `gen_ai.*` events on span events, where the OTel spec puts them) and you get the same Honeycomb-queryable columns. Bonus: the collector approach works for any GenAI instrumentation library, not just Strands — there's nothing Strands-specific about it.

OTTL transform that does the lift:

```yaml
processors:
  transform/lift_event_attrs:
    trace_statements:
      - context: spanevent
        statements:
          - merge_maps(span.attributes, attributes, "upsert")
          - keep_keys(attributes, [])

  filter/drop_empty_events:
    traces:
      spanevent:
        - 'true'
```

`spanevent` context runs once per span event. `span.attributes` is the parent span's attrs (writable from this context); `merge_maps(target, source, "upsert")` copies the event's attrs onto the parent span. The `filter` then drops every span event (now redundant). Wire both into a `traces` pipeline and the gen_ai message arrays land as columns on the parent span.

**Tradeoff:** producer-side (`LANGFUSE_BASE_URL`) is zero infrastructure but Strands-specific and depends on a substring heuristic that could change. Collector-side requires running a collector but is portable, doesn't relyon Strands internals, and gives you a place to do other ingest hygiene (PII redaction, attribute renaming, sampling, provenance stamping).

**Don't do both.** With the env var set AND the collector lift, the gen_ai message arrays land twice — once from Strands' direct `set_attributes` call, once from the collector's `merge_maps`. They overwrite to the same value (the operation is `upsert`), so it's harmless but wasteful. Pick one. If you're starting with the env var and bringing up a collector later, drop the env var when you wire the collector in.

If you need a collector deployment recipe, see `notes/skills/otel-collector-on-lambda/SKILL.md` (this project deploys "Boswell" — an OTel collector as a Lambda Function URL — that does exactly this lift). For the provenance-stamping pattern that pairs with it, see `notes/skills/collector-pipeline-provenance/SKILL.md`.

## Verification

After running the agent once, confirm the data lands as queryable columns. Honeycomb's OTLP receiver fans span events out into separate rows alongside spans, so always filter `duration_ms > 0` to look at *spans only*, not the event rows.

### Verify gen_ai.* columns exist as individual fields

Use Honeycomb MCP `find_columns` (or the dataset schema UI) and search for `gen_ai`. You should see:

- `gen_ai.usage.{input,output,total}_tokens`, `gen_ai.usage.cache_read_input_tokens`, `gen_ai.usage.cache_write_input_tokens`
- `gen_ai.server.time_to_first_token`, `gen_ai.server.request.duration`
- `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`
- `gen_ai.tool.{name,description,json_schema,status,call.id}`
- `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.agent.name`

If you see a single `metadata` column instead, the OpenInference processor is still installed. Remove it.

### Verify messages are on spans, not just on events

```json
{
  "calculations": [{"op": "COUNT"}],
  "breakdowns": ["name"],
  "filters": [
    {"column": "gen_ai.input.messages", "op": "exists"},
    {"column": "duration_ms", "op": ">", "value": 0}
  ],
  "time_range": "10m"
}
```

Expected: rows for `chat`, `execute_event_loop_cycle`, `execute_tool <name>`, `invoke_agent <name>` etc. — span names that match Strands' real spans.

If the only result is `gen_ai.client.inference.operation.details` (and it has `duration_ms = 0`), the messages are still only on span events. The `LANGFUSE_BASE_URL` value isn't tripping the heuristic. **The substring `"langfuse"` must appear literally in the value** — `LANGFUSE_BASE_URL=force-span-attrs` won't work; `LANGFUSE_BASE_URL=langfuse-anything` will.

A 5-line probe script confirms it without sending any traffic:

```python
import os
from strands.telemetry.tracer import Tracer

t = Tracer()
print(f"use_latest_genai_conventions = {t.use_latest_genai_conventions}")  # need True
print(f"is_langfuse                  = {t.is_langfuse}")                    # need True
```

Both must be `True` before there's any point shipping a trace.

## Why this works (one-paragraph version)

Strands has its own OTel GenAI instrumentation that emits well-shaped `gen_ai.*` attributes following the spec. The spec says message bodies belong on span *events*, which is correct for log-style backends but wrong for column-oriented backends like Honeycomb. The OpenInference Strands processor exists to translate Strands' GenAI shape into Phoenix's OpenInference schema, but it does so by also stuffing leftover attrs into a single JSON blob — bad for any column-oriented UI. Skipping the processor, setting `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`, and then either tripping the `is_langfuse` heuristic with `LANGFUSE_BASE_URL=langfuse-*` (no collector) or running the OTTL `merge_maps` lift in a collector (see § 4) gets you clean, individual, queryable columns plus messages on spans.

## Source-of-truth code references

If Strands changes any of this, re-check these locations in `strands-agents`:

- `strands/telemetry/tracer.py` — `_parse_semconv_opt_in`, `is_langfuse` property, `_add_event` (the `to_span_attributes` flag is the load-bearing knob).
- Search for `gen_ai_latest_experimental` and `gen_ai_tool_definitions` to find every place either flag changes behavior.
- The `openinference-instrumentation-strands-agents` package's `processor.py` — `_add_metadata` is the function that bundles `gen_ai.*` into a single JSON column. If you're seeing that, this skill should not be in use.
