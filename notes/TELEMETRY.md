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

## Next slice: drop the redundant span events — via OTel collector as Lambda

Currently each LLM-call span in Honeycomb has both:
- the JSON-encoded `gen_ai.{input,output}.messages` attrs on the span (good, queryable)
- the `gen_ai.client.inference.operation.details` span events that carry the same payload (redundant — they show up in Honeycomb as separate rows with `name=gen_ai.client.inference.operation.details, duration_ms=0`)

Producer-side options were both unsatisfying:

1. **`SpanProcessor.on_end`:** can't mutate. `ReadableSpan` is read-only by design. Reaching into `span._events` / `span._attributes` works but pins us to private SDK internals.
2. **Wrapping `OTLPSpanExporter.export`:** doable but brittle — every SDK upgrade is a chance for the wrap to drift.

The collector's `transform` processor (OTTL) was built for exactly this. `merge_maps(span.attributes, attributes, "upsert")` in the `spanevent` context lifts every event attr onto the parent span; the `filter` processor then drops the now-empty events so Honeycomb doesn't show duration-zero noise.

To avoid running a persistent collector for mom-volume traffic, we ship the collector **as a Lambda container** (`collector/` module). AgentCore's OTel exporter points at a Function URL; the Lambda transforms and forwards to Honeycomb. Cold start (~1–2 s) is invisible to mom because export is async on AgentCore's side.

Module is intentionally self-contained so it can be `cp -r`'d to other projects. Auth is bearer token in a header (Function URL is `auth_type=NONE`; we accept the security tradeoff in exchange for not having to write a Sigv4-signing OTel exporter on the AgentCore side).

Reference points if we ever revisit producer-side instead:
- `strands/telemetry/tracer.py:241` (`_add_event`) — the `to_span_attributes` knob.
- `strands/telemetry/tracer.py:114` (`is_langfuse`) — the heuristic we're tripping.
- All call sites with `to_span_attributes=self.is_langfuse`: lines 357, 417, 472, 563, 660, 766, 842, 864.
