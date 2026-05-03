---
name: collector-pipeline-provenance
description: When configuring an OpenTelemetry Collector that ships to Honeycomb, add three provenance attributes to every span the collector touches — a static "I was here" marker, a build-version stamp, and a per-process or per-invocation identifier — so future-you can tell which collector deployment processed which trace, distinguish traces that went through the collector from ones that bypassed it, and bisect "did the trace shape change between deploys?". Use when: setting up a new collector pipeline, adding a transform/filter processor whose effect is hard to detect downstream, debugging "why does this trace look different from that one?", running multiple collector deployments in front of the same Honeycomb dataset, or whenever the trigger phrases "collector provenance", "collector version stamp", "tag spans with collector identity", "which collector processed this", or "pipeline marker" come up.
---

Stamp every span the collector processes with three attributes that let you reverse-lookup what touched it. Cheap to add, expensive to wish you had after the fact.

## Why this matters specifically with Honeycomb

Honeycomb's column store makes attribute-based querying free. `WHERE collector.boswell exists` and `GROUP BY collector.boswell.version` are first-class operations. That changes the calculus from "more attrs = more storage" (true on metrics-store backends) to "more attrs = more dimensions to slice on, almost free." Provenance attributes earn their keep the first time you ask "did this trace go through the collector or not?"

## The three fields

For a collector you've named **`<name>`**, add to every span:

| Attribute | Source | What it answers |
| --- | --- | --- |
| `collector.<name>` | static `"washere"` (or any sentinel) | Did *this collector* touch this span? Filter on `exists` to find traces that did vs. didn't go through. |
| `collector.<name>.version` | build-time variable, ideally git short-SHA, append `-dirty` if the working tree is dirty when built | Which build of the collector processed it? Lets you bisect "did this trace shape change between deploys?". |
| `collector.<name>.invocation_id` | per-invocation or per-process identifier (see "Picking an invocation_id" below) | Which collector instance / Lambda invocation processed it? Group spans by this attr to see what was processed in the same process or warm container. |

## Mechanism: `attributes` processor + `include_metadata` on the receiver

Two pieces. **One**: the receiver has to expose request headers as metadata. **Two**: the `attributes` processor's `from_context` action reads from that metadata.

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
        # REQUIRED: without this, from_context: metadata.* sees nothing.
        include_metadata: true

processors:
  attributes/<name>:
    actions:
      - action: insert
        key: collector.<name>
        value: washere
      - action: insert
        key: collector.<name>.version
        value: ${env:<NAME>_VERSION}
      - action: insert
        key: collector.<name>.invocation_id
        from_context: metadata.x-amzn-trace-id   # or whatever per-request header your platform forwards

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [..., attributes/<name>]   # put it last so transforms run before stamping
      exporters: [...]
```

`action: insert` only writes if the key is absent. Use `upsert` if you want to overwrite existing values — but if a downstream collector also stamps `collector.<name>.*`, the `insert` semantics let upstream values win, which is usually what you want for provenance ("first collector to touch this wins").

## Picking an `invocation_id`

This is the field that varies most by deployment shape. Pick the one that distinguishes "different process / invocation" most usefully:

| Deployment | What's available | Recommendation |
| --- | --- | --- |
| **Lambda** (with Lambda Web Adapter) | `X-Amzn-Trace-Id` header forwarded by LWA — `Root=1-<epoch>-<id>;Parent=...;Sampled=...` — unique per Lambda invocation. **Note: LWA does NOT forward `Lambda-Runtime-Aws-Request-Id` as an HTTP header**, so you cannot get the Lambda function request ID directly. The X-Ray trace ID serves the same purpose for "which invocation processed this?". | `from_context: metadata.x-amzn-trace-id` |
| **Fargate / ECS / EC2 / Kubernetes** (long-running) | The collector's own `service.instance.id` (auto-generated UUID per process). | Use the `resource` processor to copy `service.instance.id` onto each span as `collector.<name>.invocation_id`. |
| **Local dev** | Hostname + process start time | Resource processor, or just skip the field — when iterating locally you usually don't need it. |

If none of these fit, you can also **generate a UUID per process at collector startup** by setting an env var in the container's entrypoint script (`export <NAME>_INSTANCE=$(uuidgen)`) and reading it via `${env:<NAME>_INSTANCE}` in `config.yaml`. Coarser than `X-Amzn-Trace-Id` (per-process, not per-invocation) but works anywhere.

## Build-stamping the version

The pattern that's worked well: take the project's git short-SHA at build time, append `-dirty` if the working tree has uncommitted changes, pass via `--build-arg`, set as `ENV` in the Dockerfile.

```dockerfile
ARG <NAME>_VERSION=unknown
ENV <NAME>_VERSION=${<NAME>_VERSION}
```

```bash
# scripts/build
SHA=$(git rev-parse --short HEAD)
if ! git diff --quiet . || ! git diff --cached --quiet .; then
  SHA="${SHA}-dirty"
fi
docker buildx build --build-arg "<NAME>_VERSION=${SHA}" ...
```

**Scope the dirty check to the directory that affects the binary** (e.g., the collector subdir), not the whole repo. Otherwise unrelated edits in `notes/`, sibling apps, etc. flag every build as dirty.

## Naming convention

Use `collector.<name>` as the prefix, where `<name>` is the same string everywhere — Lambda function name, container image name, env-var prefix, attribute prefix. One name, one identity. In this project the collector is named **Boswell** (a stenographer for one specific bot's utterances) and it stamps `collector.boswell.*`.

If you have multiple collectors in series (e.g., a per-service collector → a regional aggregator → Honeycomb), give each one its own name and let them all stamp:

```
collector.app-side
collector.app-side.version=...
collector.app-side.invocation_id=...
collector.regional-gateway
collector.regional-gateway.version=...
collector.regional-gateway.invocation_id=...
```

Now you can group/filter by either layer independently.

## Verification

After deploying, send a synthetic span through the collector. Query Honeycomb:

```
breakdowns: ['collector.<name>', 'collector.<name>.version', 'collector.<name>.invocation_id']
filters: [trace.trace_id = <your synthetic id>]
```

All three columns should be populated. If `invocation_id` is empty, the receiver doesn't have `include_metadata: true`, or the `from_context: metadata.*` reference points at a header name your platform isn't forwarding.

If both invocations from a fresh deploy show the SAME `invocation_id`, you've picked a per-process identifier on a platform where that's per-container — usually fine, but check whether you wanted per-invocation granularity.

## Reference implementation

`collector/` in this repo. Scripts/configs that exemplify each piece:
- `collector/config.yaml` — the `attributes/boswell` processor and the receiver's `include_metadata: true`.
- `collector/Dockerfile` — the `ARG`/`ENV` for `BOSWELL_VERSION`.
- `collector/scripts/build` — the SHA + dirty-check logic.
- `collector/scripts/smoke` — sends a span; query Honeycomb after to confirm provenance attrs land.
