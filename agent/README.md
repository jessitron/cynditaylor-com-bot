# agent/

The Strands agent: parse inbound email, edit the site, push, reply.

Source layout:
- `cyndibot.py` — agent definition (system prompt, tool wiring).
- `inbound.py` — `parse_inbound` tool (S3 → MIME → text + attachments).
- `tools/` — `site_tools.py`, `email_tools.py`.
- `server.py` — HTTP entrypoint for AgentCore / local container (`/ping`, `/invocations`).
- `observability.py` — OTel setup (`session.id` on Resource, Honeycomb-shaped Strands columns).
- `hello.py` — minimal Strands → Bedrock smoke.
- `_fetch_secret.py` — Secrets Manager fetch for `GITHUB_TOKEN` (called from container entrypoint).

The container entrypoint that wraps `server.py` lives at `scripts/container-entrypoint`.

## Build

```bash
scripts/container-build       # docker buildx --platform linux/arm64 → cyndibot:local
scripts/container-push-ecr    # ecr login, tag, push to <acct>.dkr.ecr...:latest
```

## Run locally

Direct against Bedrock (no container, no AgentCore):

```bash
scripts/hello                 # one-shot Strands invocation
scripts/agent-inbound [s3_key]   # full agent loop on an S3 inbound (newest by default)
```

Inside the container (mirrors AgentCore):

```bash
scripts/container-run-local           # foreground docker run, mounts ~/.aws ro
scripts/container-wait-ready          # poll /ping up to 60s
scripts/container-smoke-ping          # curl /ping
```

## Deploy to AgentCore

The full ship-it pipeline:

```bash
scripts/agentcore-deploy      # build → push-ecr → update → wait-ready
```

Granular pieces:

```bash
scripts/agentcore-create          # first-time runtime creation
scripts/agentcore-update          # update env vars / container image
scripts/agentcore-wait-ready      # poll get-agent-runtime until READY
scripts/agentcore-env-dry-run     # preview env vars without applying
scripts/secret-create-github-token  # create/rotate GITHUB_TOKEN secret
```

## Smoke tests

Local agent (no container, against Bedrock):

```bash
scripts/agent-fake-roundtrip      # synthetic inbound, full LLM loop, reply self-loops to S3
scripts/agent-picture-roundtrip   # HEIC + JPEG attachment flow through the LLM loop
scripts/pretend-mom-roundtrip     # real SES self-loop (pretend-mom@ → S3 → agent → reply → S3)
scripts/smoke-agent-push          # agent-initiated push to LIVE main (creates a real commit)
scripts/smoke-parse-attachments   # parse_inbound only — no LLM, no commit
scripts/smoke-push-site           # push HEAD to throwaway branch, verify, delete
scripts/smoke-send-reply          # SES SendEmail probe
```

Container HTTP server:

```bash
scripts/container-smoke-invoke    # POST /invocations with staged greeting
scripts/container-smoke-push      # docker cp + run _smoke_push_site.py inside the container
```

AgentCore (cloud):

```bash
scripts/agentcore-smoke-invoke    # invoke-agent-runtime against the deployed runtime
```

## Debug helpers

```bash
scripts/ses-show-inbound      # cat newest S3 inbound MIME
scripts/ses-list-verified     # list SES identities (sandbox membership check)
scripts/ses-verify-email <addr>   # add an address identity (recipient must click verification mail)
scripts/check-collector       # send a synthetic span to the local collector
```

## Telemetry

OTel → Honeycomb in both envs. Local: a small `otel-collector-contrib` container (`./run`, config in `collector/config.local.yaml`) listens on `localhost:4318` and forwards to the "local" Honeycomb env. Cloud: the Boswell collector Lambda forwards to env `cynditaylor-com-bot`. See `notes/TELEMETRY.md` for current shape and gotchas. Use the Honeycomb MCP to inspect traces.

## Related components

- `lambda/invoke_agent/` — SES → Lambda → AgentCore dispatcher. Deploy/smoke scripts under `lambda/invoke_agent/scripts/`. See `infra/README.md`.
- `collector/` — Boswell OTel collector lambda. See `collector/README.md`.
- `infra/README.md` — one-time AWS setup commands (SES, Route 53, S3, IAM).
