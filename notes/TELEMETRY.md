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

The full setup (with traps and verification queries) is captured as a Claude Code skill at `notes/skills/strands-honeycomb-tracing/SKILL.md` so other agents can replicate it. The skill documents both the producer-side `LANGFUSE_BASE_URL` trick and the collector-side OTTL `merge_maps` alternative — pick one, don't run both.

## Done: drop the redundant span events — Boswell ✅

Built `collector/` (a.k.a. **Boswell**), an OTel collector as a Lambda container fronted by a Function URL. Producer points its OTLP exporter at the URL; the collector lifts span-event attrs onto the parent span (OTTL `transform` with `merge_maps`), drops the now-empty events (`filter` with `'true'`), stamps three provenance attributes (`collector.boswell.*`), and forwards to Honeycomb synchronously (no batch, no sending queue — Lambda freezes between invocations).

**Current state (2026-05-03):**
- Boswell deployed at `https://45exz5ki5veyvldhaojdynf3ty0pqnno.lambda-url.us-west-2.on.aws/`. Bearer token in `collector/.env` (gitignored).
- **AgentCore is wired to Boswell.** `scripts/_build_agentcore_env_json.py` now requires `BOSWELL_FUNCTION_URL` and `INGEST_BEARER_TOKEN` and ships traces via the collector. `scripts/agentcore-update` sources `collector/.env` and resolves the function URL via `aws lambda get-function-url-config`. Verified via smoke invoke: spans land in Honeycomb stamped with `collector.boswell="washere"` (version `2b18738`). Pre-wiring spans don't have the attribute, so `WHERE collector.boswell exists` cleanly separates "via Boswell" from legacy traffic.
- `scripts/agentcore-env-dry-run` prints the env-var JSON without applying — handy when fiddling with the wiring.
- Skills written: `notes/skills/otel-collector-on-lambda/SKILL.md` (the deployment shape, six gotchas paid in blood) and `notes/skills/collector-pipeline-provenance/SKILL.md` (the three-attribute pattern).

**`LANGFUSE_BASE_URL` is no longer set on the producer.** The env var used to trip Strands' `is_langfuse` heuristic so messages landed as span attributes. Boswell's OTTL `transform/lift_event_attrs` does the same job from the collector side — verified after removal: all 3 `chat` spans in the post-cutover smoke trace still have `gen_ai.input.messages` and `gen_ai.output.messages` populated as columns. Trace `e9fc3ef5995897f7f9ad8e3265e145b5` is the reference.

If we ever pull Boswell back out of the path, restore `LANGFUSE_BASE_URL=langfuse-stub-for-honeycomb` to keep the columns. Reference points in Strands:
- `strands/telemetry/tracer.py:241` (`_add_event`) — the `to_span_attributes` knob.
- `strands/telemetry/tracer.py:114` (`is_langfuse`) — the heuristic.
- All call sites with `to_span_attributes=self.is_langfuse`: lines 357, 417, 472, 563, 660, 766, 842, 864.

## Done: stamp `session.id` on every agent span ✅

`session.id` (OTel semconv-standard) now lands as a queryable column on every span the agent emits — `agent.invocation`, `invoke_agent Strands Agents`, `execute_event_loop_cycle`, `chat`, `bedrock.converse_stream`, `execute_tool *`. Verified 2026-05-03 in Honeycomb dataset `cynditaylor-com-bot`: 13/13 spans of the cloud smoke trace `smoke-first-cloud-invoke-1777840418-cyndibot-runtime` carry the column. Cross-dataset join with the dispatcher's `cyndibot-dispatcher` events now works on a single column name.

Two changes were load-bearing:

1. **`bedrock_agentcore.runtime.context.RequestContext`** — AgentCore inspects the entrypoint signature and, if it sees `(payload, context)` (parameter literally named `context`), passes the request context with `.session_id` populated from the `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header. `agent/server.py::invoke` now takes the context and passes `session_id` into `_get_agent`.
2. **`session.id` as a Resource attribute, not a span attribute.** AgentCore guarantees one microVM per session for the microVM's entire lifetime (see [AWS docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html): "Each user session in AgentCore Runtime receives its own dedicated microVM"). So setting `session.id` on the `Resource` at first-invoke time is correct for the whole process — no SpanProcessor or contextvar plumbing needed. Honeycomb flattens resource attrs to direct columns, so `WHERE session.id = X` queries just work.

`agent/observability.py::configure_tracing` takes an optional `session_id` and stamps it on the Resource. The local non-AgentCore path (`agent/inbound.py`) calls it without a session_id and emits no `session.id` column — fine, since there's no upstream session to join to.

A wrapping span `agent.invocation` was added in `invoke()` so each AgentCore call has a clean root we own; the explicit per-span `set_attribute("session.id", …)` was removed once the Resource approach landed (redundant).

Caveat: this is semconv-pragmatic, not semconv-pure. `session.id` is defined as a span/event attribute in OTel. Putting it on Resource leans on the AgentCore microVM-per-session guarantee — if we ever ran the agent server in a process that handled multiple sessions concurrently, the column would silently lie. Not a real risk for this codebase, but worth noting for skill writeups.
