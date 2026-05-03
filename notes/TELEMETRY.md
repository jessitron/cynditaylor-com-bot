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

## Done: drop the redundant span events — Boswell ✅

Built `collector/` (a.k.a. **Boswell**), an OTel collector as a Lambda container fronted by a Function URL. Producer points its OTLP exporter at the URL; the collector lifts span-event attrs onto the parent span (OTTL `transform` with `merge_maps`), drops the now-empty events (`filter` with `'true'`), stamps three provenance attributes (`collector.boswell.*`), and forwards to Honeycomb synchronously (no batch, no sending queue — Lambda freezes between invocations).

**Current state (2026-05-03):**
- Boswell deployed at `https://45exz5ki5veyvldhaojdynf3ty0pqnno.lambda-url.us-west-2.on.aws/`. Bearer token in `collector/.env` (gitignored).
- AgentCore is **NOT yet pointed at it.** `scripts/_build_agentcore_env_json.py` still ships traces direct to Honeycomb. To flip: replace `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` with the function URL + `/v1/traces` and the Honeycomb team header with `authorization=Bearer <token>`. See `collector/README.md` § "Wiring this project's AgentCore runtime".
- Orphan resources from the rename: ECR repo `cyndibot-collector` and IAM role `CyndibotCollectorLambda` still exist (free, but worth deleting eventually).
- Skills written: `notes/skills/otel-collector-on-lambda/SKILL.md` (the deployment shape, six gotchas paid in blood) and `notes/skills/collector-pipeline-provenance/SKILL.md` (the three-attribute pattern).

**Producer-side decisions still live:**
- `LANGFUSE_BASE_URL=langfuse-stub-for-honeycomb` — keeps Strands writing JSON message arrays as span attributes alongside the events. The collector cleanup makes the events redundant; we *could* unset this once Boswell is wired in, but the duplication is harmless and removing the env var is a separate cleanup.

Reference points if we ever revisit producer-side instead:
- `strands/telemetry/tracer.py:241` (`_add_event`) — the `to_span_attributes` knob.
- `strands/telemetry/tracer.py:114` (`is_langfuse`) — the heuristic we're tripping.
- All call sites with `to_span_attributes=self.is_langfuse`: lines 357, 417, 472, 563, 660, 766, 842, 864.
