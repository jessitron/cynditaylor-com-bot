# Active plan

## Current state

The full email → edit → reply pipeline runs end-to-end in cloud. Mom emails `*@cyndibot.jessitron.honeydemo.io` → SES inbound → S3 (raw MIME) → `lambda/invoke_agent/` dispatcher (wired into the `cyndibot-inbound` receipt rule) → AgentCore Runtime `cyndibot-o2gGSvB6Hz` (us-west-2) → Strands agent → site repo commit+push → SES reply. Site-edit tools: `parse_inbound`, `send_reply`, `sync_workspace`, `list_site_files`, `read_site_file`, `write_site_file`, `delete_site_file`, `view_site_image`, `image_info`, `edit_images` (subagent), `commit_site_changes`, `push_site_changes`. Image tools in `agent/tools/image_tools.py` + `agent/image_subagent.py`. `GITHUB_TOKEN` is in AWS Secrets Manager, fetched by the container at startup. Boswell OTel collector lambda (`collector/`) sits between AgentCore and Honeycomb.

Not yet built: SES production-access (still in sandbox — outbound replies only go to verified addresses).

## Decisions locked in so far

- **AWS account:** jessitron-sandbox (`414852377253`), region `us-west-2`.
- **Model:** Claude Sonnet 4.5 via Bedrock inference profile `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. Must use inference-profile IDs, not bare model IDs.
- **Repo strategy:** clone `cynditaylor-com` into AgentCore session storage at `/mnt/workspace/cynditaylor-com`, commit via shelled `git`. Reset to `origin/main` at start of each invoke.
- **Session model:** one AgentCore `runtimeSessionId` per email **thread** (`thread-<sha256(thread-root-Message-ID)>`, JWZ-lite over References / In-Reply-To / own Message-ID). 14-day idle TTL is plenty. New thread → fresh microVM → clean Strands `_agent`; replies in the same thread reuse the warm microVM's conversation history. Each Lambda invocation gets its own `invocation.id` (uuid4) so individual emails inside a thread are still distinguishable. The dispatcher passes `s3_key`, `email_thread_id`, `invocation_id`, `email_from` in the AgentCore payload; the agent stamps them on its `agent.invocation` root span and on the Resource. Shipped 2026-05-04 — see [slice-thread-scoped-session.md](slice-thread-scoped-session.md).
- **Conversation memory:** no new store. Inbound SES message (landing in S3) + SES sent-log + git log on the site repo are authoritative. Strands `FileSessionManager` in session storage is convenience, not source of truth.
- **Observability:** OTel → Honeycomb in both environments. Locally a small `otel/opentelemetry-collector-contrib` container (`./run`, config in `collector/config.local.yaml`) listens on `localhost:4318` and forwards to the Honeycomb "local" env. In cloud, the same shape runs as the Boswell collector lambda (`collector/`) forwarding to env `cynditaylor-com-bot` under team `modernity`. Canonical shape and what's left in `notes/TELEMETRY.md`.
- **Build tooling:** `uv`.
- **Site repo:** `github.com/jessitron/cynditaylor-com`
- **Intake channel:** email via SES (pivoted off Twilio SMS because US toll-free / 10DLC compliance was disproportionate for a 1:1 bot).
- **Email domain:** `cyndibot.jessitron.honeydemo.io`, a subdomain of the Route 53 zone `jessitron.honeydemo.io.` (`Z0975156EQFWS502JWNW`).
- **Inbound trigger:** the `cyndibot-inbound` receipt rule has **two** actions, run in order:
  1. S3 action writes raw MIME to `s3://cyndibot-incoming-emails/emails/` — the source of truth, replayable.
  2. Lambda action fires the dispatcher (`lambda/invoke_agent/`), which parses the SES notification (`mail.source`, `receipt.action.bucketName`, `receipt.action.objectKey`), derives the email-thread id, and calls `bedrock-agent-core.InvokeAgentRuntime` with `runtimeSessionId = thread-<sha256(...)>` (see the session-model bullet above). Lambda returns immediately; AgentCore runs the agent asynchronously in its own microVM. Rejected alternatives: SES → Lambda alone (no durable audit trail, DIY retries on body fetch); S3 event → Lambda (more moving parts, weaker link back to SES for debugging).

## Telemetry work

Tracked separately in `notes/TELEMETRY.md` — Honeycomb-friendly tracing is done; the next telemetry slice (drop redundant span events) lives there. Touch it independently of the agent slices below.
