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

### Done: SES outbound ✅

Per https://aws.amazon.com/ses/pricing/ — $0.0001/message sent.

| Span | Attribute | Value |
| --- | --- | --- |
| `execute_tool send_reply` | `cost.ses.send.qty` | 1 |
| `execute_tool send_reply` | `cost.ses.send.price` | 0.0001 |

Constant in `agent/tools/email_tools.py` (`SES_SEND_PRICE_USD`).

**SES inbound costs (per-message receipt + chunk charge) belong to the dispatcher**, not the agent. The dispatcher is the SES integration layer; the agent only reads from S3. Inbound cost telemetry lives in `lambda/invoke_agent` (or should, when added there). The `cost.ses.receipt.*` and `cost.ses.receipt_chunks.*` attrs were briefly stamped on the agent's parse span and have been removed.

### Done: attachment visibility ✅

Non-cost observability on `execute_tool parse_inbound`:

- `email.attachment.count` — total `image/*` MIME parts on the inbound
- `email.attachment.bytes_total` — sum of decoded sizes (when count > 0)
- `email.attachment.types` — comma-joined final content-types (when count > 0)

HEIC conversion is its own child span `convert_heic_to_jpg` (one per HEIC) carrying `image.original_filename`, `image.input_bytes`, `image.output_bytes`, `image.target_path`. Wall time is span timing — no separate `heic_conversion_ms` attr. One span per attachment is fine for typical multi-photo emails; if mom ever sends 50 we can revisit.

Verified Phoenix trace `10e00b18f421d939a51c6cf49d6b528d` (later traces will also show the new `convert_heic_to_jpg` child spans).

For "find picture-bearing emails," query the agent dataset directly: `WHERE email.attachment.count > 0`. Cross-dataset joins on `session.id` give you the matching dispatcher events without needing to mirror the count.

### Future: S3 GetObject from parse_inbound

The agent reads the raw MIME from S3 in `parse_inbound`. Real cost (~$0.0004 per 1000 GET + data transfer out, but we're in-region so transfer is free). One GET per email. Tiny, but worth wiring up when we do the rollup so the bill is complete:

```
cost.s3.get.qty   = 1
cost.s3.get.price = 0.0000004
```

Stamp on the parse span. Constant goes in `agent/tools/email_tools.py`. Lowest priority.

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
SUM(cost.ses.send.qty * cost.ses.send.price)
  + SUM(cost.s3.get.qty * cost.s3.get.price)
  + SUM(cost.bedrock.input.qty * cost.bedrock.input.price)
  + SUM(cost.bedrock.output.qty * cost.bedrock.output.price)
  + SUM(cost.agentcore.cpu_seconds.qty * cost.agentcore.cpu_seconds.price)
  + SUM(cost.agentcore.gb_seconds.qty * cost.agentcore.gb_seconds.price)
  + SUM(cost.lambda.ms.qty * cost.lambda.ms.price)
GROUP BY session.id
```

(Plus `cost.ses.receipt.*` / `cost.ses.receipt_chunks.*` from the dispatcher dataset — joined on `session.id` at query time.)

A Honeycomb derived column per term keeps the dashboard query short.

### Open questions still to resolve

- **Where does the price table live?** Currently inline constants in the relevant module. Fine for one service; gets messy across four. Candidates: (a) a single `agent/pricing.py`, (b) collector-side stamping for the cloud path, (c) Honeycomb derived columns. Decide when we add Bedrock — that's the second service and forces the question.
- **Skill writeup.** Once two cost sources land with the qty/price pattern, capture as `notes/skills/cost-telemetry/` so the convention travels.
