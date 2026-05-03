# Telemetry

Tracing/observability work. Agent feature pipeline lives in `notes/ACTIVE.md`.

## Where traces go

- **Local: Arize Phoenix** — `http://localhost:6006/v1/traces` (docker, started by `./run`). Project `cynditaylor-com-bot`.
- **Cloud: Honeycomb** — team `modernity`, env `cynditaylor-com-bot`. Producer → Boswell collector → Honeycomb.
- `.env` (gitignored) holds all OTel vars locally.
- **After any run that emits traces, report the trace URL.** Locally: `scripts/check-last-span` / `scripts/check-last-trace`. Cloud: surface the Honeycomb trace ID from AgentCore output.

## Current state

- **Strands emits Honeycomb-shaped columns.** Removed `openinference-instrumentation-strands-agents` (its `metadata` JSON blob wasn't queryable). `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` makes Strands emit `gen_ai.{input,output}.messages` JSON arrays + `gen_ai.usage.*`, `gen_ai.server.*`, `gen_ai.tool.*` as columns. `BedrockInstrumentor` stays — it writes OpenInference natively. Phoenix lost its chat UI as a side effect; cloud is the production target.
- **Boswell** (`collector/`) — OTel collector as a Lambda container behind a Function URL. OTTL `merge_maps` lifts span-event attrs onto parent spans, drops empty events, stamps `collector.boswell.{,version,invocation_id}`, forwards synchronously to Honeycomb. URL `https://45exz5ki5veyvldhaojdynf3ty0pqnno.lambda-url.us-west-2.on.aws/`. AgentCore is wired through it. `WHERE collector.boswell exists` separates new traffic from legacy.
- **`session.id` on every span.** AgentCore passes `session_id` via `RequestContext` when the entrypoint signature is `(payload, context)`. `agent/observability.py::configure_tracing` stamps it as a **Resource** attribute — sound because AgentCore guarantees one microVM per session ([docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html)). Honeycomb flattens resource attrs to columns; cross-dataset joins with the dispatcher work on a single column.

## Gotchas worth keeping

- `LANGFUSE_BASE_URL` is **not** set on the producer — Boswell's `lift_event_attrs` does that job from the collector side. If Boswell ever leaves the path, restore `LANGFUSE_BASE_URL=langfuse-stub-for-honeycomb` so messages stay on spans (Strands' `is_langfuse` heuristic at `strands/telemetry/tracer.py:114` flips `to_span_attributes`; call sites at 357, 417, 472, 563, 660, 766, 842, 864).
- `session.id`-on-Resource is semconv-pragmatic, not pure. Would silently lie if one process ever handled concurrent sessions.
- Skills: `notes/skills/strands-honeycomb-tracing/`, `notes/skills/otel-collector-on-lambda/`, `notes/skills/collector-pipeline-provenance/`.
- Probe: `scripts/_probe_strands_langfuse.py` checks `is_langfuse` + `use_latest_genai_conventions` without sending a trace.

## Future direction: show the full cost of one email

Goal: one Honeycomb query that returns dollars-per-session (or per email, per user) across every service we pay for. With `session.id` already on every span, the cross-service join is free — what's missing is a `cost.<service>.usd` attribute on the right span for each cost source.

Cost sources, roughly in order of dollar magnitude:

1. **Bedrock tokens.** Data is already there: `gen_ai.usage.input_tokens` / `output_tokens` per `chat` span, plus `gen_ai.request.model`. Need a model→price table (Sonnet 4.5 vs. Opus 4.7, input vs. output rates) and a place to multiply. Two options: (a) stamp `cost.bedrock.usd` at span-finish via a SpanProcessor, or (b) leave it as a derived column in Honeycomb. (b) is cheaper to build and easier to update when prices change.
2. **AgentCore runtime.** Billed on microVM time × configured vCPU/memory. The `agent.invocation` span already gives us wall time; multiply by the runtime config. **Open question:** does AgentCore publish actual-vs-configured CPU/memory anywhere (CloudWatch metrics, response headers)? If only configured is exposed, our cost number will be an upper bound — fine for now, worth noting. Stamp `cost.agentcore.usd` on the root span.
3. **SES.** Per-message pricing, trivially countable. One stamp on the inbound-handling span + one on each `send_reply` tool span. The cheapest piece, but the easiest to wire — good first move to prove the pattern end-to-end.
4. **Boswell Lambda.** Smallest dollar amount (ms × 512MB per invoke), but visible only if we surface it. Options: (a) Lambda Insights → CloudWatch → Honeycomb metrics, (b) have the collector emit a self-span carrying `cost.lambda.usd`, (c) periodic CloudWatch pull. (a) is the standard path; (b) keeps everything in traces and joins on `session.id` for free if we propagate it.

**Roll-up query** (once attributes exist):

```
SUM(cost.bedrock.usd) + SUM(cost.agentcore.usd) + SUM(cost.ses.usd) + SUM(cost.lambda.usd)
GROUP BY session.id
```

**Sequencing suggestion:** SES → Bedrock → AgentCore → Lambda. SES is the simplest end-to-end demo of the pattern; Bedrock has the data already and just needs a multiplier; AgentCore has the open question about actual-vs-configured; Lambda is the smallest payoff and best left for last. Capture as a skill once the first two land.

**Open questions to resolve before starting:**

- Where does the price table live? (Hard-coded in code, env var, S3 JSON, Honeycomb derived-column expression?) Prices change; want one place to update.
- Stamp at span-creation, span-end, or via a separate processor? Span-end is cleanest because token counts aren't known earlier.
- Do we want `cost.*.usd` at the leaf span only, or rolled up onto the root too? Honeycomb can `SUM` across descendants in trace queries, so leaf-only is probably enough.
