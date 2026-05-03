---
name: otel-collector-on-lambda
description: Deploy the OpenTelemetry Collector as an AWS Lambda container image, fronted by a Function URL, so a low-traffic OTLP/HTTP data path can be post-processed (OTTL transforms, filters, attribute redaction, routing) without paying for persistent compute. Use when you'd want a Collector but the volume doesn't justify a Fargate task, or when the producer is itself serverless (AgentCore, API Gateway-backed Lambdas) and you want to keep the whole pipeline serverless. Trigger phrases: "OTel collector on Lambda", "collector as Lambda", "serverless OTel collector", "Lambda Function URL OTLP", "Lambda Web Adapter OTel", "ship traces through a Lambda before Honeycomb". Six gotchas paid in blood are documented inline; skim them before you start.
---

Run the OTel Collector as a Lambda container image fronted by a Function URL. Producers send OTLP/HTTP to the URL; the collector transforms; Honeycomb (or any OTLP backend) gets the result. Cold start ≈ 4 s, warm invocations ≈ 2–4 ms. At low volume it's effectively free.

## When this fits — and when it doesn't

**Fits:** mom-volume / personal-project / low-QPS data paths where you'd otherwise pay $9/mo for a 0.25 vCPU Fargate task that idles 99.9% of the time. Producer is a Lambda or AgentCore (so cold start is invisible — export is async on their side). Goal is light post-processing (OTTL `transform`, `filter`, `attributes`, `redaction`).

**Doesn't fit:**
- Sustained > ~1 req/sec — Lambda's per-invocation overhead and freeze-no-batch cost outweigh Fargate.
- You need cross-invocation queuing/retry (Honeycomb 5xx for minutes — Lambda can't buffer through that; producer-side retry is your only safety net).
- Tail sampling that needs all spans of a trace at once. Lambda invocations don't share state.
- Anything pushing logs/metrics — you can do it but the freeze problem is worse there (periodic readers don't fire while frozen).

## Six gotchas (read these first)

These cost a real afternoon when we built it. Each one fails silently or with a misleading symptom.

### 1. The official contrib image is distroless and runs as `USER 10001`

Lambda's container runtime trips on this. `USER root` won't work because there's no `/etc/passwd`. **Stage the binary into Alpine** in a multi-stage build:

```dockerfile
FROM otel/opentelemetry-collector-contrib:0.151.0 AS collector
FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=collector /otelcol-contrib /app/otelcol-contrib
```

### 2. `CMD` only — no `ENTRYPOINT`

Lambda's container init treats CMD-only and ENTRYPOINT+CMD differently. With `ENTRYPOINT` set, the main process never starts; you'll see LWA polling localhost forever (`app is not ready after 2000ms`, then 4000ms…) and the init phase will time out at 10 s. With `CMD` only, it works.

```dockerfile
CMD ["/app/otelcol-contrib", "--config=/etc/otel/config.yaml"]
```

I don't fully understand the underlying reason, but it reproduced across three base-image variants (distroless, `provided:al2023`, alpine). The LWA examples in upstream all use CMD-only. Match them.

### 3. `--provenance=false --sbom=false` on `docker buildx`

Default buildx output is an OCI image manifest with attestations. Lambda rejects it with:

```
InvalidParameterValueException: The image manifest, config or layer media type
for the source image ... is not supported.
```

Fix:

```bash
docker buildx build --platform linux/arm64 --provenance=false --sbom=false --load -t name:tag .
```

### 4. Function URL with `auth_type=NONE` needs TWO permission statements

As of an October 2025 change, `lambda:InvokeFunctionUrl` alone is no longer enough — you also need `lambda:InvokeFunction` with the `--invoked-via-function-url` qualifier. Missing the second one returns **403 `AccessDeniedException`** at the URL gate with **zero log lines anywhere** (Lambda doesn't even invoke the container). You'll spend hours debugging your auth/SCPs/account if you don't know this.

```bash
aws lambda add-permission \
  --function-name <name> \
  --statement-id FunctionURLAllowInvokeUrl \
  --action lambda:InvokeFunctionUrl \
  --principal '*' \
  --function-url-auth-type NONE

aws lambda add-permission \
  --function-name <name> \
  --statement-id FunctionURLAllowInvoke \
  --action lambda:InvokeFunction \
  --principal '*' \
  --invoked-via-function-url
```

The 403 has a body referencing https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html — that page documents the dual-permission rule; read it if symptom recurs.

### 5. No `batch` processor, no async `sending_queue`

Lambda freezes the container after each invocation handler returns. Anything sitting in a `batch` processor or in the exporter's `sending_queue` never flushes — it stays in memory until the next cold start (which discards it) or the next invocation (which may or may not happen). Symptom: collector returns 200 to LWA in milliseconds, but Honeycomb never sees the trace.

The fix is **synchronous export per request**. No batching, no queuing.

```yaml
processors:
  # NOT batch — Lambda freezes between invocations.
  transform/...:
    ...

exporters:
  otlphttp/honeycomb:
    endpoint: ${env:HONEYCOMB_OTLP_ENDPOINT}
    headers:
      x-honeycomb-team: ${env:HONEYCOMB_API_KEY}
    sending_queue:
      enabled: false   # required, not optional, on Lambda
```

The "real" fix is the `decouple` processor from the `opentelemetry-lambda/collector` distro, but that's not in `otel/opentelemetry-collector-contrib`. Synchronous export is fine at low volume.

### 6. OTel SDK has no Sigv4 → Function URL must be `auth_type=NONE`

`auth_type=AWS_IAM` would require Sigv4-signing the OTLP requests on the producer side. The OTel Python SDK doesn't do that, and writing a custom signing exporter is more code than this whole module. Pragmatic answer: `auth_type=NONE` on the Function URL, enforce a bearer token inside the collector via the `bearertokenauth` extension. The function URL hostname is unguessable random; if the bearer leaks, regenerate.

```yaml
extensions:
  bearertokenauth/ingest:
    scheme: Bearer
    token: ${env:INGEST_BEARER_TOKEN}

receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
        auth:
          authenticator: bearertokenauth/ingest

service:
  extensions: [bearertokenauth/ingest]
```

Producer sets:
```
OTEL_EXPORTER_OTLP_HEADERS=authorization=Bearer <token>
```

## Minimum-viable Dockerfile

```dockerfile
FROM otel/opentelemetry-collector-contrib:0.151.0 AS collector

FROM alpine:3.20
RUN apk add --no-cache ca-certificates

COPY --from=collector /otelcol-contrib /app/otelcol-contrib
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.0 /lambda-adapter /opt/extensions/lambda-adapter
COPY config.yaml /etc/otel/config.yaml

ENV AWS_LWA_PORT=4318
ENV AWS_LWA_INVOKE_MODE=buffered
ENV AWS_LWA_READINESS_CHECK_PATH=/

CMD ["/app/otelcol-contrib", "--config=/etc/otel/config.yaml"]
```

Why each line:
- **Multi-stage:** the official contrib image is distroless; we want Alpine for compatibility (gotcha #1).
- **`ca-certificates`:** the otlphttp exporter does HTTPS to `api.honeycomb.io`; Alpine ships without CA roots by default.
- **LWA at `/opt/extensions/`:** Lambda discovers extensions in this directory automatically. LWA registers as an extension AND ships a Runtime Interface Client, so you don't need a separate RIC. ([README confirms.](https://github.com/awslabs/aws-lambda-web-adapter))
- **`AWS_LWA_PORT=4318`:** the OTLP/HTTP receiver listens here; LWA forwards Function URL invocations to `localhost:4318`.
- **`AWS_LWA_INVOKE_MODE=buffered`:** buffered = single response per request (correct for OTLP). The other option, `response_stream`, is for SSE/streaming responses.
- **`AWS_LWA_READINESS_CHECK_PATH=/`:** LWA polls this path until something responds before forwarding traffic. The OTLP receiver returns 404 on `/` but that counts as "ready" (any HTTP response).
- **`CMD` only, no `ENTRYPOINT`:** gotcha #2.

## Build / push / deploy commands

```bash
# Build (gotcha #3 inline)
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --sbom=false \
  --load \
  -t collector:local .

# Push
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-west-2
REPO=collector
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
docker tag collector:local "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:latest"
docker push "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:latest"

# Lambda + Function URL (assumes role and ECR repo already exist)
aws lambda create-function \
  --function-name collector \
  --package-type Image \
  --code "ImageUri=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:latest" \
  --role "arn:aws:iam::$ACCOUNT:role/CollectorLambda" \
  --architectures arm64 \
  --memory-size 512 \
  --timeout 30 \
  --environment "Variables={...}"
aws lambda wait function-active-v2 --function-name collector

aws lambda create-function-url-config --function-name collector --auth-type NONE
# BOTH permissions (gotcha #4)
aws lambda add-permission \
  --function-name collector \
  --statement-id FunctionURLAllowInvokeUrl \
  --action lambda:InvokeFunctionUrl \
  --principal '*' \
  --function-url-auth-type NONE
aws lambda add-permission \
  --function-name collector \
  --statement-id FunctionURLAllowInvoke \
  --action lambda:InvokeFunction \
  --principal '*' \
  --invoked-via-function-url
```

## Verification flow

After deploy, send a synthetic OTLP request and confirm three things:

1. **Function URL accepts auth.** Quick curl:
   ```bash
   curl -i -X POST "${URL}v1/traces" \
     -H 'Content-Type: application/x-protobuf' \
     -H "Authorization: Bearer ${TOKEN}" \
     --data-binary 'x'
   ```
   Expected: **400** (collector parses an invalid OTLP body and rejects). 403 means the URL gate is rejecting (gotcha #4 not done correctly). 401 means bearer is wrong.

2. **A real OTLP request succeeds.** Use the OTel SDK with `OTLPSpanExporter` and `SimpleSpanProcessor`, capture the export result. Don't use `BatchSpanProcessor` — batching on the producer side is fine, but for verification you want the result return value to be the export status.

3. **The trace lands in Honeycomb.** Query by trace_id or by service name. If the export reported success but Honeycomb shows nothing, you didn't disable `sending_queue` (gotcha #5).

## CloudWatch volume budget

Approximate per-trigger:
- **Cold start:** ~12 lines (collector startup banners + Lambda runtime START/END/REPORT).
- **Warm invocation:** 3 lines (just Lambda's START/END/REPORT — the collector itself emits nothing during steady state).
- **Container retirement** (Lambda recycles after ~minutes idle): 4 lines (graceful shutdown).

At 100 invocations/day with one cold start, that's ~315 lines/day, ~10 KB/day. CloudWatch ingest is $0.50/GB; you'd need decades to cross a dollar.

## Reference implementation

`collector/` in `cynditaylor-com-bot`. Self-contained module — `cp -r collector/ ../other-project/`, edit `config.env` to rename, edit `config.yaml` to swap processors. The `scripts/` are: `bootstrap`, `build`, `validate-config`, `push-ecr`, `deploy`, `smoke`, `delete`, `redeploy`, `logs`, `dump-recent-logs`, `count-logs`. All idempotent and named so you don't have to remember command shapes.
