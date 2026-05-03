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

## Cost telemetry: full cost of one email

Goal: one Honeycomb query returns dollars-per-session (or per email, per user) across every service we pay for. With `session.id` already on every span, the cross-service join is free.

**Shape we settled on:** stamp `cost.<service>.<line>.qty` and `cost.<service>.<line>.price` (USD) on whichever span is currently active when the cost is incurred. Total dollars stay computed at query time (`SUM(qty * price)`) — that way prices can be updated by editing one constant without rewriting historical data, and the qty/price split makes the bill auditable.

We're tracking marginal post-free-tier cost — not the actual AWS bill. Free-tier accounting is a different question.

### Done: SES ✅

Per https://aws.amazon.com/ses/pricing/ — both directions are $0.0001/message.

| Span | Attribute | Value |
| --- | --- | --- |
| `execute_tool parse_inbound` | `cost.ses.receipt.qty` | 1 |
| `execute_tool parse_inbound` | `cost.ses.receipt.price` | 0.0001 |
| `execute_tool send_reply` | `cost.ses.send.qty` | 1 |
| `execute_tool send_reply` | `cost.ses.send.price` | 0.0001 |

Constants live in `agent/tools/email_tools.py` (`SES_SEND_PRICE_USD`, `SES_RECEIPT_PRICE_USD`). Verified locally — Phoenix trace `12299e69d2997939859c149b9ba46ac1` (`scripts/agent-fake-roundtrip` run 2026-05-03) carries all four attributes on the right two spans.

### Next: SES inbound chunk charge (becomes load-bearing once Mom sends pictures)

SES bills $0.00009 per 256KB chunk of incoming mail on top of the per-message charge. For plain-text emails (~5KB) the chunk charge is ~10% of inbound; for a 1MB photo it's ~half of inbound and dominates.

`parse_inbound_impl` already has `raw` bytes in scope. Add:

```python
chunks = max(1, math.ceil(len(raw) / (256 * 1024)))
span.set_attribute("cost.ses.receipt_chunks.qty", chunks)
span.set_attribute("cost.ses.receipt_chunks.price", 0.00009)
```

Verify with a fake inbound large enough to need >1 chunk.

### Next: Bedrock tokens

Token counts are already on `chat` spans as `gen_ai.usage.input_tokens` / `output_tokens`, and the model is on `gen_ai.request.model`. Need a model→price table:

- Sonnet 4.5: $3 per 1M input tokens, $15 per 1M output tokens
- Opus 4.7: $15 per 1M input tokens, $75 per 1M output tokens

Pattern:

```
cost.bedrock.input.qty   = input_tokens
cost.bedrock.input.price = price_in_per_token   # per token, not per million
cost.bedrock.output.qty  = output_tokens
cost.bedrock.output.price = price_out_per_token
```

Open question: producer-side stamp (Strands span-end hook or wrap `BedrockInstrumentor`) vs. collector-side enrichment in Boswell (one place that knows all prices, no producer redeploys when prices change). Lean toward collector-side since Boswell already does attribute manipulation — but means the cost data only exists in the cloud path, not local Phoenix. Decide before writing code.

### Next: AgentCore runtime

Billed on microVM time × configured vCPU/memory. `agent.invocation` span has wall time; need configured vCPU/RAM from the runtime config. Open: does AgentCore expose actual-vs-configured CPU/memory anywhere (CloudWatch namespace, response headers)? If only configured is exposed, our number is an upper bound — call it out in the attribute name or accept the imprecision.

### Next: Boswell Lambda

Smallest dollar amount (ms × 512MB per invoke). Two paths:
- Lambda Insights → CloudWatch metrics → pull into Honeycomb. Standard, but breaks the "everything in traces" property.
- Have the collector emit a self-span carrying `cost.lambda.{ms.qty, ms.price}`. Keeps the join on `session.id` if we propagate it; need to attach the self-span to the right trace context.

Lowest priority — do last.

### Roll-up query (once all four cost sources exist)

```
SUM(cost.ses.receipt.qty * cost.ses.receipt.price)
  + SUM(cost.ses.receipt_chunks.qty * cost.ses.receipt_chunks.price)
  + SUM(cost.ses.send.qty * cost.ses.send.price)
  + SUM(cost.bedrock.input.qty * cost.bedrock.input.price)
  + SUM(cost.bedrock.output.qty * cost.bedrock.output.price)
  + SUM(cost.agentcore.cpu_seconds.qty * cost.agentcore.cpu_seconds.price)
  + SUM(cost.agentcore.gb_seconds.qty * cost.agentcore.gb_seconds.price)
  + SUM(cost.lambda.ms.qty * cost.lambda.ms.price)
GROUP BY session.id
```

A Honeycomb derived column per term keeps the dashboard query short.

### Open questions still to resolve

- **Where does the price table live?** Currently inline constants in the relevant module. Fine for one service; gets messy across four. Candidates: (a) a single `agent/pricing.py`, (b) collector-side stamping for the cloud path, (c) Honeycomb derived columns. Decide when we add Bedrock — that's the second service and forces the question.
- **Skill writeup.** Once two cost sources land with the qty/price pattern, capture as `notes/skills/cost-telemetry/` so the convention travels.
