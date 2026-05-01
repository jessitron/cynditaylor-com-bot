# Telemetry

Tracing/observability work, tracked separately from the agent feature pipeline. The agent's product slices live in `notes/ACTIVE.md`; this file is for OTel/Phoenix/Honeycomb shape.

## Where traces go

- **Local dev: Arize Phoenix** (self-hosted via docker, endpoint `http://localhost:6006/v1/traces`). Started by `./run`. Project name `cynditaylor-com-bot` (from `OTEL_SERVICE_NAME`).
- **Cloud (AgentCore runtime): Honeycomb**, team `modernity`, env `cynditaylor-com-bot`. Endpoint + ingest key are passed as AgentCore `environmentVariables`.
- Bedrock spans are auto-instrumented by `openinference-instrumentation-bedrock`.
- `.env` has all the OTel vars locally and is gitignored.
- **After any test run that emits traces, report the trace URL.** Locally: `scripts/check-last-span` / `scripts/check-last-trace` print URLs of the form `http://localhost:6006/projects/{projectId}/traces/{traceId}`. For cloud runs, surface the Honeycomb trace ID from the AgentCore invoke output.

## Done: Honeycomb-friendly tracing ✅

Strands' OTel telemetry now lands in Honeycomb as queryable individual columns (`gen_ai.usage.*`, `gen_ai.server.{time_to_first_token,request.duration}`, `gen_ai.tool.*`, `gen_ai.{input,output}.messages` on real spans) instead of an opaque `metadata` JSON blob. Three changes were load-bearing:

1. Removed `openinference-instrumentation-strands-agents` and its `StrandsAgentsToOpenInferenceProcessor`. The processor was bundling unmapped attrs into a single JSON `metadata` column that Honeycomb couldn't query. Phoenix lost its chat-style UI in exchange — acceptable since cloud is the production target. `BedrockInstrumentor` from `openinference-instrumentation-bedrock` stays, since it writes OpenInference attrs natively (no translation phase).
2. Set `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` so Strands emits `gen_ai.input.messages`/`output.messages` JSON arrays (Honeycomb AI view shape) instead of legacy per-message events.
3. Set `LANGFUSE_BASE_URL=langfuse-stub-for-honeycomb` to trip Strands' `is_langfuse` heuristic — substring `"langfuse"` is what matters (the rest is documentation). With the flag tripped, Strands also calls `span.set_attributes(...)` for those JSON arrays alongside `span.add_event(...)`. Without the trip, messages live only on span events; Honeycomb's columnar queries can't reach them.

`scripts/_probe_strands_langfuse.py` — 5-line check that confirms `is_langfuse` and `use_latest_genai_conventions` are both `True` without sending a trace. Useful to flip first when something's wrong.

The full setup (with traps and verification queries) is captured as a Claude Code skill at `notes/skills/strands-honeycomb-tracing/SKILL.md` so other agents can replicate it.

## Next slice: drop the redundant span events

Currently each LLM-call span in Honeycomb has both:
- the JSON-encoded `gen_ai.{input,output}.messages` attrs on the span (good, queryable)
- the `gen_ai.client.inference.operation.details` span events that carry the same payload (redundant — they show up in Honeycomb as separate rows with `name=gen_ai.client.inference.operation.details, duration_ms=0`)

Goal: consolidate. Two sub-questions for this slice:

1. **Cheap version:** custom OTel `SpanProcessor` whose `on_end` walks `span.events`, hoists any unique event-attrs onto the span itself (with a prefix like `event.<event_name>.<attr>` to avoid collisions). Doesn't drop the events; just makes sure no field is event-only.
2. **Full version:** wrap the OTLP exporter so it filters span events out of the serialized payload before send. Events on a `ReadableSpan` are immutable at `on_end` time — must intercept later. The OTLP exporter does its own serialization in `OTLPSpanExporter.export()`; subclass it or wrap it with an exporter-decorator pattern.

Reference points to read in `strands-agents`:
- `strands/telemetry/tracer.py:241` (`_add_event`) — the `to_span_attributes` knob.
- `strands/telemetry/tracer.py:114` (`is_langfuse`) — the heuristic we're tripping.
- All call sites with `to_span_attributes=self.is_langfuse`: lines 357, 417, 472, 563, 660, 766, 842, 864.

Do (1) first, see if Honeycomb is happy without the events being filtered out (they're cheap to ignore in queries — just `WHERE duration_ms > 0`). If event noise is actually hurting, do (2).
