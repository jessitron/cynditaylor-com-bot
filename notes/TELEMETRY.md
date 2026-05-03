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
- **AgentCore is wired to Boswell.** `scripts/_build_agentcore_env_json.py` now requires `BOSWELL_FUNCTION_URL` and `INGEST_BEARER_TOKEN` and ships traces via the collector. `scripts/agentcore-update` sources `collector/.env` and resolves the function URL via `aws lambda get-function-url-config`. Verified via smoke invoke: spans land in Honeycomb stamped with `collector.boswell="washere"` (version `2b18738`). Pre-wiring spans don't have the attribute, so `WHERE collector.boswell exists` cleanly separates "via Boswell" from legacy traffic.
- `scripts/agentcore-env-dry-run` prints the env-var JSON without applying — handy when fiddling with the wiring.
- Orphan resources from the rename: ECR repo `cyndibot-collector` and IAM role `CyndibotCollectorLambda` still exist (free, but worth deleting eventually).
- Skills written: `notes/skills/otel-collector-on-lambda/SKILL.md` (the deployment shape, six gotchas paid in blood) and `notes/skills/collector-pipeline-provenance/SKILL.md` (the three-attribute pattern).

**Producer-side decisions still live:**
- `LANGFUSE_BASE_URL=langfuse-stub-for-honeycomb` — keeps Strands writing JSON message arrays as span attributes alongside the events. The collector cleanup makes the events redundant; we *could* unset this once Boswell is wired in, but the duplication is harmless and removing the env var is a separate cleanup.

Reference points if we ever revisit producer-side instead:
- `strands/telemetry/tracer.py:241` (`_add_event`) — the `to_span_attributes` knob.
- `strands/telemetry/tracer.py:114` (`is_langfuse`) — the heuristic we're tripping.
- All call sites with `to_span_attributes=self.is_langfuse`: lines 357, 417, 472, 563, 660, 766, 842, 864.

## TODO: stamp `session.id` on every agent span

The dispatcher Lambda's per-email events (dataset `cyndibot-dispatcher`) carry `session.id = mom-<sha256(from)>` — same value the dispatcher passes to AgentCore as `runtimeSessionId`. The agent's traces (dataset `cynditaylor-com-bot`) do **not** currently have a `session.id` column at all (verified 2026-05-03 via `find_columns`). Strands and `BedrockInstrumentor` don't emit it, and AgentCore doesn't inject it.

Goal: add `session.id` (OTel semconv-standard name) as a span attribute on every agent span, with the same value the dispatcher used. Then the dispatcher's per-email event row joins to the agent's trace by a single column name across two datasets.

Sketch:
- `agent/server.py::invoke(payload)` is the AgentCore entrypoint; it currently only receives `{"s3_key": ...}`. The `runtimeSessionId` is set by the caller (`bedrock-agentcore.invoke_agent_runtime(runtimeSessionId=...)`) and is available to the running container — check whether AgentCore exposes it via env var or request context (e.g. `bedrock_agentcore` SDK), or have the dispatcher add it to the payload as a fallback.
- Once read, set as a span attribute on the entrypoint span and propagate via `Resource` or a `SpanProcessor` so all child spans inherit it.
