# Running the OpenTelemetry Collector as a Lambda

The OpenTelemetry Collector is usually deployed as a long-running process: a sidecar, a DaemonSet, an EC2 instance, a docker container on my computer. It sits there listening for telemetry. That's fine when I want to send telemetry all day, but not when telemetry is rare. Like right now, when I have an agent defined on AgentCore, and it runs a few times a week maybe. Or my website that hardly sees any traffic.

Can I run the OpenTelemetry Collector as a Lambda function? Sounds tricky, but hey, that's what my coding assistant is for! Here is how we got it working:

(from here, this post is agent-written, edited by me)

You can package the OTel Collector as a Lambda container image and front it with a Function URL. Producers send OTLP/HTTP to the URL; the collector runs whatever processors you configure; the result goes on to your backend.

At low volume this costs essentially nothing: a Lambda below the free tier rounds to zero. Cold start is around 4 seconds; warm invocations are 2–4 ms.

## When this fits

The Lambda shape works when:

- Traffic is intermittent — single-digit requests per second peak, often zero.
- The producer exports asynchronously (a `BatchSpanProcessor`, an AgentCore runtime, another Lambda) so cold start is invisible to the user.
- The processing you want is stateless per request — OTTL `transform`, `filter`, `attributes`, redaction, routing.

It does not fit when:

- Sustained throughput exceeds about 1 request per second. Lambda's per-invocation overhead and pricing stop being free.
- You need queuing or retry. If the backend is briefly unavailable, in-Lambda retry state dies with the process. Producer-side retry is your only safety net.
- You're scraping metrics or logs. This is only for logs and traces that are pushed to the collector.

## Architecture

```
Producer (any OTLP/HTTP client)
   │  OTLP/HTTP/protobuf, bearer token in Authorization header
   ▼
Lambda Function URL  (auth_type=NONE; bearer enforced inside the collector)
   │
Lambda container image
   ├─ AWS Lambda Web Adapter (extension)
   │    polls the Lambda Runtime API, forwards each invocation as an HTTP
   │    request to localhost:4318
   └─ otelcol-contrib  (CMD, not ENTRYPOINT)
        ├─ otlp receiver (bearertokenauth)
        ├─ your processors
        └─ otlphttp exporter (sending_queue disabled)
             → backend (e.g. api.honeycomb.io)
```

[AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter) is the load-bearing piece. It registers as a Lambda extension, exposes the Lambda Runtime API as an HTTP listener on a port of your choosing, and forwards each invocation to your container's HTTP server. The Collector's OTLP/HTTP receiver is an HTTP server. LWA bridges them.

**A note on auth.** The bearer token in the diagram is optional but recommended. The Collector's OTLP receiver works without it. But a Function URL with `auth_type=NONE` is publicly reachable, so without a check inside the collector, anyone who learns the URL can send data through it to your backend — running up your ingest bill and polluting your telemetry. The hostname is random, but URLs leak (commit history, screenshots, packet captures). A static bearer token, shared between authorized producers and this Lambda, raises the bar from "anyone with the URL" to "anyone with the URL and the token." Details in the Authentication section below.

## The container image

Use a multi-stage build. The official `otel/opentelemetry-collector-contrib` image is distroless and runs as `USER 10001` with no `/etc/passwd`, both of which the Lambda container runtime trips on. Copy the binary into Alpine and run from there.

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

What each piece does:

- **`ca-certificates`** — Alpine ships without trusted CA roots. The `otlphttp` exporter does HTTPS to the backend; without this it fails at TLS.
- **LWA at `/opt/extensions/`** — Lambda discovers extensions in this directory automatically at container start. LWA ships its own Runtime Interface Client, so you do not need a separate RIC.
- **`AWS_LWA_PORT=4318`** — The OTLP/HTTP receiver's default port. LWA forwards Function URL invocations here.
- **`AWS_LWA_INVOKE_MODE=buffered`** — One response per request. The other option, `response_stream`, is for Server-Sent Events.
- **`AWS_LWA_READINESS_CHECK_PATH=/`** — LWA polls this path until something responds before forwarding traffic. The OTLP receiver returns 404 on `/`, which counts as ready (any HTTP response is enough).
- **`CMD`, not `ENTRYPOINT`** — Lambda treats CMD-only and ENTRYPOINT+CMD images differently at boot. With ENTRYPOINT set, the main process never starts. See troubleshooting below.

## The configuration

Three things shape the config: the receiver needs bearer-token auth, the processing must be stateless per request, and the exporter must not queue.

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

processors:
  # Your processors here. Examples: transform/, filter/, attributes/.
  # Do NOT include a batch processor.

exporters:
  otlphttp/honeycomb:
    endpoint: https://api.honeycomb.io
    headers:
      x-honeycomb-team: ${env:HONEYCOMB_API_KEY}
    sending_queue:
      enabled: false

service:
  extensions: [bearertokenauth/ingest]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [...]
      exporters: [otlphttp/honeycomb]
```

This sends to Honeycomb. To send elsewhere, swap the exporter — any OTLP/HTTP backend works with the same shape (change the `endpoint` and the auth header name and value).

Two non-obvious settings:

- **No `batch` processor.** Lambda freezes the container after the handler returns. Spans sitting in a `batch` processor never flush — they stay in memory until the next cold start (which discards them) or the next invocation (which may or may not arrive). Symptom: the exporter reports 200 in milliseconds, the backend never sees the trace.
- **`sending_queue.enabled: false`** on every exporter. Same reason. The default async queue holds spans in memory; the freeze strands them.

The official fix for these is the `decouple` processor from the `opentelemetry-lambda` collector distribution, which knows to flush before the handler returns. It is not in `otel/opentelemetry-collector-contrib`. If you stick with the contrib image, synchronous export is the correct shape.

### Authentication

Bearer auth is optional but recommended; see the note in Architecture for why. This section covers how.

Function URLs support `auth_type=AWS_IAM` and `auth_type=NONE`. IAM would be the strict answer, but it requires Sigv4-signing the OTLP requests on the producer side, and the OpenTelemetry SDKs do not sign with Sigv4. Writing a Sigv4-signing OTLP exporter is more work than this whole pattern is worth.

The pragmatic answer is `auth_type=NONE` on the Function URL plus the `bearertokenauth` extension inside the collector. The bearer token is a shared secret between the producer's environment and the Lambda's environment. If it leaks, rotate it.

The producer sets:

```
OTEL_EXPORTER_OTLP_HEADERS=authorization=Bearer <token>
```

The header name is case-insensitive at the receiver. The token value is not.

If you skip bearer auth, drop the `extensions` block, the `auth:` stanza on the receiver, and the `extensions: [bearertokenauth/ingest]` line under `service`. Everything else in the config is the same.

## Building, pushing, deploying

### Build

```bash
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --sbom=false \
  --load \
  -t collector:local .
```

`--provenance=false --sbom=false` are required. Default `buildx` output is an OCI image manifest with attestations, which Lambda rejects with `InvalidParameterValueException: The image manifest, config or layer media type for the source image ... is not supported`.

### Push to ECR

Push the image to ECR. The ECR repository needs to exist first; see [Appendix: ECR setup](#ecr-setup) for the one-time commands.

### Create the Lambda

The Lambda needs an execution role with `AWSLambdaBasicExecutionRole` and a trust policy that lets `lambda.amazonaws.com` assume it; see [Appendix: Lambda execution role](#lambda-execution-role) for the one-time setup.

```bash
aws lambda create-function \
  --function-name collector \
  --package-type Image \
  --code "ImageUri=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:latest" \
  --role "arn:aws:iam::$ACCOUNT:role/CollectorLambda" \
  --architectures arm64 \
  --memory-size 512 \
  --timeout 30 \
  --environment "Variables={INGEST_BEARER_TOKEN=...,HONEYCOMB_API_KEY=...}"

aws lambda wait function-active-v2 --function-name collector
```

512 MB and 30 s are comfortable defaults. The collector itself uses much less; allocating more memory gives Lambda proportionally more CPU, which shortens cold start.

### Create the Function URL

```bash
aws lambda create-function-url-config \
  --function-name collector \
  --auth-type NONE
```

### Permissions — both statements are required

This is general Lambda Function URL behavior as of October 2025, not specific to the collector — but it's the single most common silent failure when first deploying, so it lives here in the main flow rather than in an appendix. `lambda:InvokeFunctionUrl` alone is not sufficient to allow public Function URL invocations; you also need `lambda:InvokeFunction` with `--invoked-via-function-url`:

```bash
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

Without the second statement, every request gets a 403 `AccessDeniedException` at the URL gate and Lambda does not invoke the container — there are no CloudWatch log lines to debug from. AWS documents the dual-permission rule at <https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html>.

## Verification

After deploy, send a synthetic OTLP request and check three things.

**1. The URL gate accepts auth.** Send an invalid body with the correct bearer:

```bash
curl -i -X POST "${URL}v1/traces" \
  -H 'Content-Type: application/x-protobuf' \
  -H "Authorization: Bearer ${TOKEN}" \
  --data-binary 'x'
```

Expected: **400**. The collector parses the invalid OTLP body and rejects it. A 400 here means the Function URL accepted the request, LWA forwarded it, and the collector ran. If you see 403, see troubleshooting. If you see 401, the bearer token in the producer doesn't match the one in the Lambda's environment.

**2. A real OTLP request succeeds.** Use any OTel SDK with `OTLPSpanExporter` and a `SimpleSpanProcessor` (not `BatchSpanProcessor` — for verification you want the export's return value to reflect the actual export status). Capture the result of `span_exporter.export(...)`. It should be `SUCCESS`. For a curl-only alternative, the `sample-span.json` + curl pattern in [Testing an OpenTelemetry Collector deployed as a Daemonset in Kubernetes](https://jessitron.com/2023/09/08/testing-an-opentelemetry-collector-deployed-as-a-daemonset-in-kubernetes/) works the same way against a Function URL — point the curl at `${URL}v1/traces` and add the bearer header.

**3. The span lands in your backend.** Query by trace ID or service name. If you're sending to Honeycomb, the [Honeycomb MCP server](https://github.com/honeycombio/honeycomb-mcp) lets your editor or CLI query traces directly — `get_trace` with the trace ID returns the span shape without opening the UI, which makes "did my one test span land" a one-line check. If the producer reported `SUCCESS` but the backend shows nothing, the most likely cause is an enabled `sending_queue` or a `batch` processor — see troubleshooting.

## CloudWatch volume

Approximate per-invocation log output:

- **Cold start:** ~12 lines (collector startup banners plus Lambda runtime START/END/REPORT).
- **Warm invocation:** 3 lines (Lambda runtime only; the collector emits nothing during steady-state processing at `info` level).
- **Container retirement** (Lambda recycles containers after idle): 4 lines (graceful shutdown).

At 100 invocations per day with one cold start, this is roughly 315 lines and 10 KB per day — about 4 MB per year. At CloudWatch's $0.50/GB ingest rate, that's roughly **$0.002 per year**.

---

## Troubleshooting

Symptoms grouped by where the failure surfaces. Most of these are silent — they don't produce a useful error message — so the symptom-to-cause table matters more than usual.

### 403 `AccessDeniedException` at the Function URL, no CloudWatch log lines

The dual-permission gotcha. `lambda:InvokeFunctionUrl` alone is no longer sufficient on `auth_type=NONE` Function URLs. Add the second `lambda:InvokeFunction` statement with `--invoked-via-function-url`. See the Permissions section above.

This one is especially confusing because Lambda doesn't invoke the container at all — there are no logs anywhere, the collector is fine, and you'll spend time investigating SCPs, account-level blocks, or the resource policy itself before realizing the gate rejected the request before reaching Lambda.

### 401 from the collector

The bearer token in the request doesn't match `INGEST_BEARER_TOKEN` in the Lambda's environment. Compare them. The header name is case-insensitive but the token value is not.

### Producer reports `SUCCESS`, backend never sees the trace

A `batch` processor or an enabled `sending_queue` is holding spans in memory across the Lambda freeze. Remove the batch processor and set `sending_queue.enabled: false` on every exporter.

You can confirm this is the cause by setting the collector's log level to `debug` temporarily — you'll see the spans arrive at the exporter but no export attempt before the invocation ends. Set it in `config.yaml`:

```yaml
service:
  telemetry:
    logs:
      level: debug
```

Rebuild and redeploy. Switch back to `info` once you've diagnosed the issue; `debug` is noisy enough to matter for CloudWatch volume.

### `InvalidParameterValueException: image manifest ... is not supported` when creating the function

Default `docker buildx` output is an OCI image manifest with build attestations, which Lambda's image-pull path rejects. Rebuild with `--provenance=false --sbom=false`.

### LWA logs `app is not ready after 2000ms` repeatedly, then init times out at 10 s

The collector process never started. One cause is having both `ENTRYPOINT` and `CMD` in the Dockerfile — Lambda's container init handles CMD-only and ENTRYPOINT+CMD images differently, and with `ENTRYPOINT` set the main process doesn't come up. Use `CMD` only. This reproduces across distroless, `provided:al2023`, and Alpine bases; it is a Lambda-runtime behavior, not a base-image issue.

Less common: the collector started but bound to a different port than `AWS_LWA_PORT`. Confirm the OTLP receiver's HTTP endpoint matches.

### Container won't start; logs mention permissions or `/etc/passwd`

You might be running the official `otel/opentelemetry-collector-contrib` image directly. It is distroless and runs as `USER 10001` with no `/etc/passwd`. Stage the binary into Alpine via a multi-stage build instead.

### `x509: certificate signed by unknown authority` from the exporter

Alpine base without `ca-certificates`. Add `RUN apk add --no-cache ca-certificates` to the Dockerfile.

### Cold start is much longer than 4 seconds

Increase `--memory-size`. Lambda allocates CPU proportional to memory; at 128 MB the cold start can run into double-digit seconds. 512 MB is a comfortable default for the contrib binary.

### Function URL is reachable but every request returns 500 with no detail

Check the collector's logs in CloudWatch. The most common causes are a missing required env var (the config references `${env:FOO}` and `FOO` is not set) or an invalid config file that survived deploy because no one ran `otelcol validate` on it. Run `otelcol-contrib validate --config=/etc/otel/config.yaml` inside the built image as part of CI.

### The backend is briefly down and traces are lost

Expected. Lambda has no cross-invocation buffer; if the backend returns 5xx, the in-process retry inside that invocation runs and then the container freezes. Producer-side `BatchSpanProcessor` retry covers most short outages — that is the only buffer you have in this shape. If you need durable buffering, this pattern is the wrong fit; use a persistent collector instead.

---

## Appendix: one-time AWS setup

The main flow above assumes the ECR repository and Lambda execution role already exist. These are the one-time commands to create them.

### ECR setup

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-west-2
REPO=collector

aws ecr create-repository --repository-name "$REPO" --region "$REGION"
```

`create-repository` errors if the repo already exists; safe to ignore.

To push to it (from the main flow):

```bash
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

docker tag collector:local "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:latest"
docker push "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:latest"
```

### Lambda execution role

The role needs two pieces: a trust policy letting Lambda assume it, and a permissions policy letting it write CloudWatch logs. `AWSLambdaBasicExecutionRole` is the managed policy that covers the logs.

```bash
cat > trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name CollectorLambda \
  --assume-role-policy-document file://trust.json

aws iam attach-role-policy \
  --role-name CollectorLambda \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

The role ARN goes into `--role` on `aws lambda create-function` in the main flow.
