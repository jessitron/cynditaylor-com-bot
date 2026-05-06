# Telemetry

Tracing/observability work. Agent feature pipeline lives in `notes/ACTIVE.md`.

## Where traces go

- **Local: Arize Phoenix** — `http://localhost:6006/v1/traces` (docker, started by `./run`). Project `cynditaylor-com-bot`.
- **Cloud: Honeycomb** — team `modernity`, env `cynditaylor-com-bot`. Producer → Boswell collector → Honeycomb.
- `.env` (gitignored) holds all OTel vars locally.
- **After any run that emits traces, report the trace URL.** Locally: query the Phoenix MCP (`mcp__phoenix__list-traces`, `mcp__phoenix__get-trace`) and build `http://localhost:6006/projects/{projectId}/traces/{traceId}`. Cloud: surface the Honeycomb trace ID from AgentCore output.

## Current state

- **Strands emits Honeycomb-shaped columns.** Removed `openinference-instrumentation-strands-agents` (its `metadata` JSON blob wasn't queryable). `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` makes Strands emit `gen_ai.{input,output}.messages` JSON arrays + `gen_ai.usage.*`, `gen_ai.server.*`, `gen_ai.tool.*` as columns. `BedrockInstrumentor` stays — it writes OpenInference natively. Phoenix lost its chat UI as a side effect; cloud is the production target.
- **Boswell** (`collector/`) — OTel collector as a Lambda container behind a Function URL. OTTL `merge_maps` lifts span-event attrs onto parent spans, drops empty events, stamps `collector.boswell.{,version,invocation_id}`, forwards synchronously to Honeycomb. URL `https://45exz5ki5veyvldhaojdynf3ty0pqnno.lambda-url.us-west-2.on.aws/`. AgentCore is wired through it. `WHERE collector.boswell exists` separates new traffic from legacy.
- **`session.id` = email-thread id, on every span.** The dispatcher derives `session.id` from the email thread (`thread-<sha256(thread-root-Message-ID)>`, JWZ-lite over References / In-Reply-To / own Message-ID) and passes it as `runtimeSessionId` to AgentCore. AgentCore guarantees one microVM per session ([docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html)) — so one thread = one warm `_agent` instance with the prior conversation history; new threads get fresh microVMs and clean state. `agent/observability.py::configure_tracing` stamps `session.id` (and the redundant-but-explicit `email.thread.id` and `email.from`) as **Resource** attributes. Honeycomb flattens resource attrs to columns; cross-dataset joins with the dispatcher work on a single column. The agent's `agent.invocation` root span additionally stamps `invocation.id` (the per-Lambda-invocation uuid) so we can distinguish individual emails inside a thread.

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

Constant `SES_SEND_USD` in `agent/pricing.py`.

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

### Done: Bedrock tokens ✅

Producer-side. `agent/pricing.py` holds the model→price table (per-token, not per-million); `BedrockCostStampingProcessor` in `agent/observability.py` runs as a SpanProcessor before the BatchSpanProcessor and mutates `span._attributes` in `on_end` for spans named `chat`. Lands cost attrs in both Phoenix and Honeycomb.

Four buckets, all independent (Bedrock returns `inputTokens`, `cacheReadInputTokens`, `cacheWriteInputTokens`, `outputTokens` separately — `inputTokens` does *not* include cache tokens, so they multiply against three different prices):

| Token attribute (set by Strands) | Cost attrs stamped |
| --- | --- |
| `gen_ai.usage.input_tokens` | `cost.bedrock.input.{qty,price}` |
| `gen_ai.usage.output_tokens` | `cost.bedrock.output.{qty,price}` |
| `gen_ai.usage.cache_read_input_tokens` | `cost.bedrock.cache_read.{qty,price}` |
| `gen_ai.usage.cache_write_input_tokens` | `cost.bedrock.cache_write.{qty,price}` |

Cache prices assume the 5-minute TTL (the Bedrock default). Cache attrs are only stamped when Strands stamped the matching token attr — no zero-pad. Verified Phoenix trace `13a848fada1ab330840765a3e2ff2970` (no cache hits this run, so input/output only).

**How cache buckets compose on a single call.** Bedrock's `Converse` `usage` returns four independent counts:

- `inputTokens` — *uncached* input only. Cache reads do NOT count here.
- `cacheReadInputTokens` — tokens served from a previously-written cache entry.
- `cacheWriteInputTokens` — tokens just written this call.
- `outputTokens` — completion.

The three input-side counts never overlap; they sum to the actual prompt size. So a 12k-token prompt where 11k hit cache + 1k are new shows up as `inputTokens=1000, cacheReadInputTokens=11000, cacheWriteInputTokens=0`. Three different prices apply: $3/MTok uncached, $0.30/MTok cache read (10× cheaper, the whole point), $3.75/MTok cache write — the rollup is `qty * price` summed across all four buckets and you see the cache discount in dollars without doing subtraction.

Strands only stamps a `gen_ai.usage.cache_*` attr when Bedrock returned that field (so `qty=0` is possible but absence is also possible). Our processor's `if qty is None: continue` handles the absence case; `qty=0` still stamps and contributes 0 to the sum, which is correct.

Not yet exercised on a real cache-hit run — Strands doesn't enable Bedrock prompt caching in our config today. Code path is symmetric with input/output (verified), should just work, but worth a smoke when caching is turned on.

**Why mutate `_attributes` directly?** `Span.set_attribute` no-ops after `_end_time` is set, but `BoundedAttributes` is created with `immutable=False` and stays mutable for the span's lifetime. The same `_attributes` dict is shared between the live `Span` and the `ReadableSpan` passed to each on_end, so writes from our processor land in the version BatchSpanProcessor exports. Standard pattern; slightly hacky.

**Why producer-side over collector-side:** keeps the qty/price pattern uniform with `SES_SEND_USD`, and local Phoenix sees the same data as Honeycomb. Lambda costs will likely be collector-side later (the producer doesn't see its own runtime billing).

### Done: AgentCore runtime ✅

Billed at $0.0895/vCPU-hour and $0.00945/GB-hour ([pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)). `create-agent-runtime` has no vCPU/memory params — AgentCore auto-sizes the microVM and bills actuals. `AWS/Bedrock-AgentCore` CloudWatch metrics (`CPUUsed-vCPUHours`, `MemoryUsed-GBHours`) report actuals but only carry the runtime ARN as a dimension — no `session.id` or trace ID, so they can't be joined to a trace.

Instead: `AgentCoreCostStampingProcessor` in `agent/observability.py` snapshots `resource.getrusage(RUSAGE_SELF)` in `on_start` for spans named `agent.invocation`, computes the delta in `on_end`, and stamps four attrs:

| Attribute | Source |
| --- | --- |
| `cost.agentcore.cpu.seconds` | delta of `ru_utime + ru_stime` |
| `cost.agentcore.cpu.usd_per_hour` | constant 0.0895 |
| `cost.agentcore.memory.peak_rss_bytes` | `ru_maxrss` at on_end (×1024 on Linux, ×1 on macOS) |
| `cost.agentcore.memory.usd_per_gb_hour` | constant 0.00945 |

Honeycomb derived column for the dollar amount:

```
cpu.seconds / 3600 * cpu.usd_per_hour
+ peak_rss_bytes / 1e9 * (duration_ms / 3_600_000) * memory.usd_per_gb_hour
```

Verified Phoenix trace `2a8948fb779d9ed08cdc71e8bdbaef62` (CPU 0.65s, peak RSS 119 MB, ~17.5s wall → ~$2.2e-5 per email).

**Caveats kept for honesty:**

- **Process-RSS, not microVM allocation.** `ru_maxrss` is what the Python process holds; AgentCore bills the whole microVM (Python + sidecars + kernel buffers). We're probably 70–90% of the truth, biased low. Naming says `peak_rss_bytes` not `gb_allocated` so this stays visible.
- **`ru_maxrss` is a process high-water mark.** On a warm microVM serving many invocations, the first one establishes the baseline and later ones inherit it. Per-invocation memory cost is overstated for early invocations and understated when memory grew on a prior invocation. Roughly matches AgentCore's "allocated GB-hours" billing model so it's the right shape, just not exact.
- **CPU is accurately per-invocation** (it's a delta).
- **Smoke** in `scripts/_smoke_agentcore_cost_processor.py` exercises the processor without an exporter.

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
  + SUM(cost.bedrock.cache_read.qty * cost.bedrock.cache_read.price)
  + SUM(cost.bedrock.cache_write.qty * cost.bedrock.cache_write.price)
  + SUM(cost.agentcore.cpu.seconds) / 3600 * AVG(cost.agentcore.cpu.usd_per_hour)
  + SUM(cost.agentcore.memory.peak_rss_bytes / 1e9 * duration_ms / 3_600_000) * AVG(cost.agentcore.memory.usd_per_gb_hour)
  + SUM(cost.lambda.ms.qty * cost.lambda.ms.price)
GROUP BY session.id
```

(Plus `cost.ses.receipt.*` / `cost.ses.receipt_chunks.*` from the dispatcher dataset — joined on `session.id` at query time.)

A Honeycomb derived column per term keeps the dashboard query short.

### Open questions still to resolve

- **Skill writeup.** With three cost sources landed (SES, Bedrock, AgentCore) under the qty/price pattern, capture as `notes/skills/cost-telemetry/` so the convention travels. Trigger after Boswell Lambda lands so the skill covers both producer-side and collector-side stamping.

### Resolved: price table location

Lives in `agent/pricing.py`. Bedrock token prices, `SES_SEND_USD`, `AGENTCORE_CPU_USD_PER_HOUR`, and `AGENTCORE_MEMORY_USD_PER_GB_HOUR` all import from there. Refresh by editing one file, no rewrite of historical telemetry.
