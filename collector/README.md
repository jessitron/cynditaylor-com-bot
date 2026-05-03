# OTel Collector as a Lambda — "Boswell"

A single-purpose AWS Lambda that sits between this project's AgentCore runtime (Strands agent) and Honeycomb, post-processing OpenTelemetry traces in flight. The collector is named **Boswell** — Samuel Johnson's biographer, who recorded everything one specific person said. He stamps every span he processes with `collector.boswell.*` provenance attributes so we can tell, after the fact, exactly which spans went through him and which build did the processing.

Self-contained module: `cp -r collector/ ../other-project/`, edit `config.env` to rename, edit `config.yaml` to swap processors. When reusing, rename Boswell to whatever you want via `COLLECTOR_NAME` in `config.env`.

## What it's for and why Lambda

Two motivations stacked on top of each other.

**The processing we want.** Strands' GenAI instrumentation puts `gen_ai.{input,output}.messages` on both span attributes AND span events. The events show up in Honeycomb as duration-zero noise rows. We want to lift any event-only data onto the parent span and drop the events. A producer-side Python `SpanProcessor` can't do this — `ReadableSpan` is read-only at `on_end` time. The collector's `transform` (OTTL) processor can, in one line. See `notes/TELEMETRY.md` for the full rationale.

**Why not a persistent collector.** Mom-volume traffic — a few emails per day. A Fargate task at 0.25 vCPU / 0.5 GB is ~$9/mo and idles ~99.9% of the time. Lambda Function URL with a container image, fronted by Lambda Web Adapter, gives us the same OTLP/HTTP receiver shape and costs effectively zero at this volume. Cold start (~4 s) is invisible because the producer (AgentCore) exports asynchronously via `BatchSpanProcessor` and doesn't block on it.

The shape doesn't fit if you're sustained > ~1 req/sec, need cross-invocation queuing for retry-through-outages, or want tail sampling that needs all spans of a trace at once. For those, see the persistent-collector alternative in `notes/skills/otel-collector-on-lambda/SKILL.md`.

Built around `otel/opentelemetry-collector-contrib` + [AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter), which lets the collector's OTLP/HTTP receiver respond to Function URL invocations.

## Architecture

```
AgentCore (Strands)
   │  OTLP/HTTP/protobuf, bearer token, X-Amzn-Trace-Id from Lambda runtime
   ▼
Lambda Function URL  (auth_type=NONE — bearer enforced inside the collector)
   │
Lambda container image (Alpine + staged otelcol-contrib binary)
   ├─ Lambda Web Adapter (extension)
   │    polls Runtime API, forwards HTTP request to localhost:4318
   └─ otelcol-contrib (CMD, no ENTRYPOINT — gotcha #2)
        ├─ otlp receiver (bearertokenauth, include_metadata: true)
        ├─ transform: lift span-event attrs onto parent span
        ├─ filter:    drop the now-empty span events
        ├─ attributes: stamp collector.boswell.* provenance
        └─ otlphttp/honeycomb (sending_queue: disabled — Lambda freezes)
             → api.honeycomb.io
```

## Files

| Path | Purpose |
| --- | --- |
| `Dockerfile` | Alpine base + staged otelcol-contrib binary + LWA extension. Pinned versions. Takes `BOSWELL_VERSION` build arg. |
| `config.yaml` | Receivers, OTTL transform, filter, attributes processor, exporter. Reads secrets from env. |
| `config.env` | Module-level config (Lambda name, ECR repo, region). Edit when reusing. |
| `.env.example` | Per-deployment secrets template. Copy to `.env`, fill in. |
| `infra/role-trust.json` | Lambda execution role trust policy. |
| `scripts/bootstrap` | One-time: ECR repo, IAM role, generates bearer token. |
| `scripts/build` | `docker buildx` to a local image. |
| `scripts/validate-config` | Runs `otelcol validate` inside the image. |
| `scripts/push-ecr` | Tag + push to ECR. |
| `scripts/deploy` | Create-or-update the Lambda + Function URL. Idempotent. |
| `scripts/smoke` | Send a test span via OTLP/HTTP, assert export succeeded. |
| `scripts/delete` | Tear down Lambda + Function URL. Leaves ECR + IAM. |
| `scripts/redeploy` | Build → validate → push → deploy → smoke, in sequence. |
| `scripts/run-local` | Run the container locally for debugging, no LWA. |
| `scripts/logs` | Tail recent CloudWatch logs (`/aws/lambda/${COLLECTOR_NAME}`). |
| `scripts/dump-recent-logs` | Same logs, raw, one entry per line — handy when CW's CLI fragments tab-separated REPORT lines. |
| `scripts/count-logs` | Two-smoke window + classifier — answers "how much CloudWatch volume per invocation?". |
| `scripts/probe`, `probe-body` | curl variants against the Function URL. Distinguishes 401/403/400 to localize misconfig. |
| `scripts/diag-403`, `test-iam-auth` | One-shot diagnostics from when we were chasing the dual-permission gotcha. Kept around in case it recurs. |
| `scripts/inspect-image` | Architecture + binary type for the local image. |

## Deploy

From the module directory:

```bash
scripts/bootstrap         # ECR repo, IAM role, bearer token (idempotent)
# edit collector/.env, set HONEYCOMB_API_KEY
scripts/build             # local docker image
scripts/validate-config   # sanity-check config.yaml
scripts/push-ecr          # push to ECR
scripts/deploy            # Lambda + Function URL
scripts/smoke             # send a test span; asserts 200 from collector
```

`scripts/deploy` prints the producer-side env vars to set:

```
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://<random>.lambda-url.us-west-2.on.aws/v1/traces
OTEL_EXPORTER_OTLP_HEADERS=authorization=Bearer <token>
```

## Wiring this project's AgentCore runtime to it

`scripts/_build_agentcore_env_json.py` currently sets `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` directly to Honeycomb and adds `x-honeycomb-team`. To route through the collector instead:

1. Replace `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` with the function URL + `/v1/traces`.
2. Replace the `OTEL_EXPORTER_OTLP_HEADERS` line with `authorization=Bearer <token>` (drop the Honeycomb team header — the collector adds it on egress).
3. Re-run `scripts/agentcore-update`.

Phoenix (local dev) bypasses the collector — the cleanup is only needed on the cloud path. Leave the local exporter pointing at `http://localhost:6006/v1/traces`.

## Reuse in another project

```bash
cp -r collector/ ../other-project/
cd ../other-project/collector
# edit config.env: COLLECTOR_NAME, ECR_REPO, LAMBDA_ROLE_NAME
# edit config.yaml: tweak the OTTL statements for the project's traces
scripts/bootstrap && scripts/build && scripts/push-ecr && scripts/deploy
```

## Auth tradeoff

Function URL is `auth_type=NONE`. The collector enforces a bearer token via the `bearertokenauth` extension. Why not IAM?

IAM auth requires Sigv4-signing OTLP requests on the producer side. The OTel Python SDK doesn't sign with Sigv4, and writing a custom signing exporter is more code than this module is worth. Bearer token in a header is the pragmatic answer; the function URL host is unguessable random; if the token leaks, regenerate (`scripts/bootstrap` won't touch a non-empty token, so delete the line in `.env` first) and redeploy.

## Cost

At low traffic (mom-volume): pennies. Lambda free tier alone covers it.

If you start exceeding ~1 req/sec sustained, switch to a persistent collector (Fargate `0.25 vCPU / 0.5 GB`, ~$9/mo) — Lambda's cold-start tax and per-invocation pricing stop being free.

## OTTL cheat sheet (what's actually happening in `config.yaml`)

```yaml
transform/lift_event_attrs:
  trace_statements:
    - context: spanevent
      statements:
        - merge_maps(span.attributes, attributes, "upsert")
        - keep_keys(attributes, [])
```

`spanevent` context: each statement runs once per span event. `span.attributes` is the parent span's attrs (writable from this context). `merge_maps(target, source, "upsert")` copies source into target, overwriting on collision. `keep_keys(attributes, [])` keeps zero keys — i.e. clears the event's own attrs.

```yaml
filter/drop_empty_events:
  traces:
    spanevent:
      - 'true'
```

Filter drops items where the condition is true. `'true'` is unconditional — every span event gets dropped. If you want to keep some (e.g. exception events), change to e.g. `'name != "exception"'`.

## Provenance: what Boswell stamps on every span

The `attributes/boswell` processor in `config.yaml` adds three fields to every span the collector processes:

| Attribute | Source | What it tells you |
| --- | --- | --- |
| `collector.boswell` | static `"washere"` | Boswell touched this span. Useful as a filter (`WHERE collector.boswell exists`) to find traces that did vs. didn't go through the collector. |
| `collector.boswell.version` | git short-SHA at build time, `-dirty` if the working tree wasn't clean | Which build of Boswell processed the span. Lets you bisect "did this trace shape change between deploys?". `scripts/build` derives it via `git rev-parse --short HEAD`. |
| `collector.boswell.invocation_trace_id` | `X-Amzn-Trace-Id` header forwarded by Lambda Web Adapter | A per-Lambda-invocation marker. Format is `Root=1-<epoch>-<id>;Parent=<parent>;Sampled=<n>;Lineage=...`. The `Root=1-…` portion is unique per invocation; group spans by this attr to see which spans were processed in the same Lambda warm container. |

The `invocation_trace_id` field uses the X-Ray trace header rather than the Lambda runtime request ID because LWA doesn't forward `Lambda-Runtime-Aws-Request-Id` as an HTTP header. Functionally equivalent for "which invocation processed this?" — just framed as the X-Ray trace ID.

The receiver needs `include_metadata: true` for the `from_context: metadata.x-amzn-trace-id` lookup to work; the `attributes` processor reads request metadata only when the receiver exposes it.

## Limitations

- **No cross-invocation buffer.** Each Lambda invocation processes whatever the producer sent in that batch and exits. If Honeycomb is briefly 5xx-ing, the in-Lambda retry queue dies with the process. Producer-side `BatchSpanProcessor` retries cover most of this.
- **Cold start ~4–5 s on first request.** Invisible to the user (export is async on the producer) but adds tail latency to the very first export after idle. Subsequent invocations are 2–4 ms.
- **Traces only.** Add `metrics` / `logs` pipelines in `config.yaml` if needed.

## Gotchas (paid in blood, recorded for future-me)

These are not optional reading if you're adapting this module — each one cost an hour of debugging.

1. **`auth_type=NONE` Function URLs need TWO permission statements**, not one. As of October 2025, `lambda:InvokeFunctionUrl` alone is no longer sufficient — you also need `lambda:InvokeFunction` with `--invoked-via-function-url`. Without the second statement, every request gets 403 `AccessDeniedException` at the URL gate with NO log lines anywhere — Lambda doesn't even invoke the container. `scripts/deploy` adds both.
2. **No batch processor, no async sending queue.** Lambda freezes the container after the invocation handler returns. Anything sitting in `batch` or `sending_queue` never flushes. Synchronous export is the only correct shape. The `decouple` processor from the `opentelemetry-lambda` distro is the "real" fix but isn't in `otel/opentelemetry-collector-contrib`.
3. **Distroless contrib image doesn't work as a Lambda base.** The official `otel/opentelemetry-collector-contrib` image runs as `USER 10001` and has no `/etc/passwd`, both of which Lambda's container runtime trips over. Stage the binary into Alpine.
4. **Use `CMD` only, NOT `ENTRYPOINT` + `CMD`.** Lambda treats CMD-only and ENTRYPOINT+CMD container images differently for boot purposes. With ENTRYPOINT set, the main process never starts; with CMD only, it does. (Don't fully understand why — observed across three base-image variants.)
5. **`--provenance=false --sbom=false` on `docker buildx`.** Default buildx output is OCI image manifest with attestations, which Lambda rejects with `InvalidParameterValueException: image manifest ... is not supported`. The build script sets these.
6. **Remember the bearer token in `OTEL_EXPORTER_OTLP_HEADERS`** uses lowercase `authorization=Bearer <token>`. The OTel collector's `bearertokenauth` extension is case-insensitive on the header name but the token value is not.
