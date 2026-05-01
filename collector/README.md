# OTel Collector as a Lambda

Self-contained module: an OpenTelemetry Collector packaged as a container-image AWS Lambda, fronted by a Function URL. Use it when you need OTTL post-processing on a low-traffic OTel data path but don't want to run persistent compute.

Built around `otel/opentelemetry-collector-contrib` + [AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter), which lets the collector's OTLP/HTTP receiver respond to Function URL invocations.

## Why this exists in this project

Strands' GenAI instrumentation puts `gen_ai.{input,output}.messages` on both span attributes and span events. The events show up in Honeycomb as duration-zero noise rows. We want to lift any event-only data onto the parent span and drop the events. A Python `SpanProcessor` can't mutate `ReadableSpan`; the collector's `transform` (OTTL) processor can. See `notes/TELEMETRY.md` for the full rationale.

## Architecture

```
AgentCore (Strands)
   │  OTLP/HTTP/protobuf, bearer token
   ▼
Lambda Function URL
   │
Lambda container image
   ├─ Lambda Web Adapter (extension) → polls Runtime API, forwards HTTP to localhost:4318
   └─ otelcol-contrib
        ├─ otlp receiver (bearertokenauth)
        ├─ transform: lift span-event attrs onto parent span
        ├─ filter: drop the now-empty span events
        ├─ batch
        └─ otlphttp/honeycomb → api.honeycomb.io
```

## Files

| Path | Purpose |
| --- | --- |
| `Dockerfile` | Collector contrib image + LWA extension. Pinned versions. |
| `config.yaml` | Receivers, OTTL transform, filter, exporter. Reads secrets from env. |
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
