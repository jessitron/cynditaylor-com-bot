# Active plan

## Decisions locked in so far

- **AWS account:** jessitron-sandbox (`414852377253`), region `us-west-2`.
- **Model:** Claude Sonnet 4.5 via Bedrock inference profile `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. Must use inference-profile IDs, not bare model IDs.
- **Repo strategy:** clone `cynditaylor-com` into AgentCore session storage at `/mnt/workspace/cynditaylor-com`, commit via shelled `git`. Reset to `origin/main` at start of each invoke.
- **Session model:** one AgentCore `runtimeSessionId` per mom's email address. 14-day idle TTL is plenty.
- **Conversation memory:** no new store. Inbound SES message (landing in S3) + SES sent-log + git log on the site repo are authoritative. Strands `FileSessionManager` in session storage is convenience, not source of truth.
- **Observability:** OTel → Arize Phoenix (self-hosted locally, `http://localhost:6006/v1/traces`). Honeycomb may come later.
- **Build tooling:** `uv`.
- **Site repo:** `github.com/jessitron/cynditaylor-com` (confirmed to exist).
- **Intake channel:** email via SES (pivoted off Twilio SMS because US toll-free / 10DLC compliance was disproportionate for a 1:1 bot).
- **Email domain:** `cyndibot.jessitron.honeydemo.io`, a subdomain of the Route 53 zone `jessitron.honeydemo.io.` (`Z0975156EQFWS502JWNW`).
- **Inbound trigger:** the `cyndibot-inbound` receipt rule has **two** actions, run in order:
  1. S3 action writes raw MIME to `s3://cyndibot-incoming-emails/emails/` — the source of truth, replayable.
  2. Lambda action fires a Lambda that parses the SES notification (`mail.source`, `receipt.action.bucketName`, `receipt.action.objectKey`), reads the body from S3, and calls `bedrock-agent-core.InvokeAgentRuntime` with `runtimeSessionId = sender's email`. Lambda returns immediately; AgentCore runs the agent asynchronously in its own microVM. Rejected alternatives: SES → Lambda alone (no durable audit trail, DIY retries on body fetch); S3 event → Lambda (more moving parts, weaker link back to SES for debugging).

## Done so far

1. `pyproject.toml` + `uv`, `agent/hello.py` confirms Bedrock auth from Python.
2. OTel → Phoenix wired; Bedrock auto-instrumented via `openinference-instrumentation-bedrock`. Spans land under OpenInference project `cyndibot` (name from `OTEL_SERVICE_NAME`).
3. `hello.py` converted to a Strands Agent (no tools); 4-span traces land in Phoenix with correct OpenInference kinds (agent → chain → llm → chain) via `StrandsAgentsToOpenInferenceProcessor`.
4. Twilio send API smoke-tested, then **abandoned** — US toll-free and 10DLC both require A2P verification paperwork that's not worth it for a 1:1 bot. Scripts preserved in git history.
5. `.env` untracked (was checked in by mistake); `.env.example` committed as the template.
6. **SES inbound stood up end-to-end on `cyndibot.jessitron.honeydemo.io`:**
   - SES domain identity, DKIM verified.
   - Route 53: 3× DKIM CNAMEs + MX → `inbound-smtp.us-west-2.amazonaws.com` (priority 10).
   - S3 bucket `cyndibot-incoming-emails` with SES-scoped `PutObject` policy, all public access blocked.
   - Receipt rule `cyndibot-inbound` added to the existing active rule set `instruqt-email-ruleset` (single active rule set per region), scoped to recipient domain so it doesn't collide with the instruqt rule.
   - Verified: a real email from `jessitron@gmail.com` to `something@cyndibot.jessitron.honeydemo.io` landed in S3 in <1s, all SES verdicts (spam/virus/SPF/DKIM/DMARC) PASS.
   - All commands reproducible via `scripts/ses-*` and `scripts/route53-*`; raw commands logged in `infra/README.md`.

## Next slice: agent reads the inbound email ✅

1. ✅ `agent/tools/email_tools.py::parse_inbound(s3_key)` — pulls raw MIME from S3, returns `{from, to, subject, body_text, body_html, message_id, in_reply_to}`. Uses stdlib `email` with `policy.default`.
2. ✅ `agent/inbound.py`: Strands Agent with only `parse_inbound`. System prompt asks it to summarize sender / request / ambiguity without editing anything.
3. ✅ `scripts/agent-inbound [s3_key]` — defaults to newest object in `s3://cyndibot-incoming-emails/emails/`, runs the agent, prints the Phoenix trace URL at the end.
4. ✅ Smoke test passed: agent correctly identified a test email from `jessitron@gmail.com` with subject "does this work" and flagged the request as ambiguous. Trace landed in Phoenix under project `cynditaylor-com-bot`.

## Current slice: agent replies via SES ✅

1. ✅ `email_tools.send_reply_impl / send_reply` — boto3 `sesv2 send_email` with raw MIME, sets `From`, `To`, `Subject`, `In-Reply-To`, `References`. SES overrides client-set `Message-ID`, so tool returns just `ses_message_id`; the delivered message's ID is `<{ses_message_id}@us-west-2.amazonses.com>` — use that shape if we ever need to match replies to sent messages.
2. ✅ Agent `inbound.py` now holds both tools and a prompt that drives parse → reply.
3. ✅ `scripts/agent-fake-roundtrip` stages a synthetic inbound from `smoketest@cyndibot.jessitron.honeydemo.io`, runs the agent, and the agent's reply round-trips back into S3 via the existing receipt rule. Full dev loop, no external identity verification needed.

**Sandbox reality (correcting earlier note):** account *is* in SES sandbox (`ProductionAccessEnabled: false`). Can only send to verified identities. The cyndibot domain is verified, which is why the self-loop works. For real replies to mom / Jessitron's gmail we need either `scripts/ses-verify-email <addr>` (adds an address identity, recipient must click the verification email) or production-access approval.

## Slice: agent edits the site ✅

1. ✅ `site_tools.py`: `sync_workspace`, `list_site_files`, `read_site_file`, `write_site_file`, `commit_site_changes`. Hand-rolled over shelling to `git` rather than pulling in `strands-agents-tools` — narrower, path-validated (no `..`, no `.git/`), and the agent doesn't need a generic shell. Commit author is `Cyndibot <bot@cyndibot.jessitron.honeydemo.io>`, set at clone time.
2. ✅ Workspace lives at `./cynditaylor-com` (already in `.gitignore`); configurable via `CYNDIBOT_WORKSPACE`. For AgentCore prod we'll set that to `/mnt/workspace/cynditaylor-com`.
3. ✅ `inbound.py` prompt drives a 7-step flow: parse → decide → sync → list → read → write → commit → reply. Prompt explicitly tells the agent the commit is local-only, so the reply doesn't oversell.
4. ✅ Roundtrip verified: a "change the hero text" fake inbound produced a clean 1-line diff on `index.html`, a Cyndibot-authored commit, and a coherent reply email in S3.

## Slice: real SES inbound+outbound loop ✅

1. ✅ Verified `jessitron@jessitron.com` as an SES email-address identity (`scripts/ses-verify-email`). Real-recipient outbound confirmed via `scripts/smoke-send-reply`.
2. ✅ `scripts/pretend-mom-roundtrip` exercises the full path with no staging: SES send from `pretend-mom@cyndibot.jessitron.honeydemo.io` → SES receipt rule → S3 → agent → SES send of reply → S3.
3. **Design note:** once the Lambda is in front, it can filter by recipient username. `cyndi@cyndibot...` (or whatever we settle on) triggers the agent; `pretend-mom@`, `smoketest@`, etc. stay as test-fixture addresses that land in S3 but don't spin up agent work. Lets us seed integration data without invoking the real pipeline.
4. First real-SES run surfaced nice behavior: the pretend-mom message asked for a revert that wasn't yet on origin/main. The agent read the file, saw the target state already matched, declined to commit a no-op, and replied explaining. Prompt is doing its job.

## Slice: push to live site (tool only, not yet agent-accessible) ✅

1. ✅ `push_site_changes_impl(remote_branch="main")` shells out to `git push`; the `@tool` wrapper is no-arg and main-only. No `GITHUB_TOKEN` plumbing — relies on the local git credential helper (macOS keychain works out of the box).
2. ✅ `scripts/smoke-push-site` pushes HEAD to `origin/cyndibot-smoke-test`, verifies via `ls-remote`, deletes the branch. Auth path confirmed without touching `main`.
3. Pending decision: when do we wire `push_site_changes` into `agent/inbound.py`? Current plan is to watch one manual main-push go through first.

## Next slice: AgentCore Phase 1 — local container

Goal: a Docker container serving AgentCore's HTTP contract locally, reusing all existing tools. Verify end-to-end before touching AWS. Detailed research notes (HTTP contract, IAM, session filesystem, SDK shape, source URLs) are in `notes/agentcore-contract.md` — read that first.

Headline constraints from the contract:
- Container is **`linux/arm64`** (matters for Docker build args if dev machine is Intel).
- Serves `POST /invocations` + `GET /ping` on **`0.0.0.0:8080`**.
- `runtimeSessionId` arrives as header `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`.
- Session filesystem mounts at `/mnt/workspace` (locally simulate with a named Docker volume).
- PyPI `bedrock-agentcore` package wraps all three concerns via `BedrockAgentCoreApp` + `@app.entrypoint` — use it.

Steps:

1. Add `bedrock-agentcore` to `pyproject.toml` dependencies; `uv sync`.
2. Create `agent/server.py`:
   - Import `BedrockAgentCoreApp` from `bedrock_agentcore`.
   - `@app.entrypoint def invoke(payload): ...` that builds a Strands `Agent` with the same tools as `agent/inbound.py` and calls it with `payload["s3_key"]`. Return the agent's final message.
   - `if __name__ == "__main__": app.run()`.
   - Factor out the agent-construction code from `agent/inbound.py` into a shared helper so the CLI entrypoint and the server entrypoint don't drift.
3. `Dockerfile` (at repo root):
   - `FROM python:3.11-slim` (or `python:3.12-slim`, match `.venv`).
   - `COPY pyproject.toml uv.lock ./` and `RUN pip install uv && uv sync --frozen --no-dev`.
   - `COPY agent ./agent`.
   - `ENV CYNDIBOT_WORKSPACE=/mnt/workspace/cynditaylor-com`.
   - `ENV OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://host.docker.internal:6006/v1/traces` (overridable at runtime).
   - `CMD ["python", "-m", "agent.server"]`.
   - Target `linux/arm64`.
4. `scripts/container-build` — `docker buildx build --platform linux/arm64 -t cyndibot:local .`. Print image size + tag.
5. `scripts/container-run-local`:
   - Create a named volume `cyndibot-workspace` (simulates `/mnt/workspace`).
   - Run with `-p 8080:8080`, `-v cyndibot-workspace:/mnt/workspace`, `-v ~/.aws:/root/.aws:ro` (inherit user's AWS creds), `-e AWS_REGION=us-west-2`, `--env-file .env` (for `OTEL_*`).
   - Print `curl` one-liners for `/ping` and `/invocations`.
6. Smoke tests (separate scripts to keep commands out of chat):
   - `scripts/container-smoke-ping` — `curl -fsS localhost:8080/ping`.
   - `scripts/container-smoke-invoke` — `curl -X POST` with a payload containing the newest inbound S3 key (reuse `_pick_newest_inbound.py`). Verify agent runs, new reply lands in S3, Phoenix has a trace.
7. Verify traces still reach Phoenix from inside the container. If `host.docker.internal` resolution is flaky on this Mac, fallback is `--add-host host.docker.internal:host-gateway`.

Known gotchas to watch for:
- **Git credentials inside container**: the local mac's macOS keychain helper is not available; `push_site_changes` will fail without a `GITHUB_TOKEN` in the container env. Don't trigger push tool from local-container tests; or set `GITHUB_TOKEN` in `.env` now and use `git config credential.helper store` in the Dockerfile. For AgentCore proper, pass the token via Secrets Manager.
- **Cold-start timing**: Strands + boto3 + OTel is heavy. First `/invocations` may take 10-20s. AgentCore has a `/ping` health check — make sure the app starts the web server BEFORE constructing the Agent (lazy-initialize the Agent on first invoke), so `/ping` goes healthy fast.
- **Session filesystem semantics**: locally the Docker volume persists between `docker run`s as long as we don't `--rm` the volume, matching AgentCore's per-session persistence. Document the invariant in a comment near `sync_workspace_impl`.

## Slice after Phase 1: AgentCore Phase 2 — ship to AWS

Only start this once Phase 1 smoke tests pass locally.

1. Create ECR repo `cyndibot` in us-west-2. Log every aws-cli call in `infra/README.md`.
2. `scripts/container-push-ecr` — authenticates docker to ECR, retags `cyndibot:local` → `<account>.dkr.ecr.us-west-2.amazonaws.com/cyndibot:latest`, pushes.
3. Create IAM role `CyndibotAgentRuntime`:
   - Trust: `bedrock-agentcore.amazonaws.com`, with `aws:SourceAccount=414852377253` + `aws:SourceArn` pattern for our account's runtimes.
   - Baseline AgentCore permissions (see `notes/agentcore-contract.md` § IAM).
   - Plus: `s3:GetObject`/`PutObject` on `cyndibot-incoming-emails/*`, `ses:SendEmail` for the bot From address, and (if push is enabled) `secretsmanager:GetSecretValue` on the GITHUB_TOKEN secret.
   - Write role JSON to `infra/iam/cyndibot-agent-runtime-*.json` so it's reviewable.
4. Store `GITHUB_TOKEN` in Secrets Manager (`cyndibot/github-token`). Update `site_tools.sync_workspace_impl` so it can pull the token from env (already works) but add a container-entrypoint shim that fetches the secret into env on boot.
5. `aws bedrock-agentcore-control create-agent-runtime` with the shape from `notes/agentcore-contract.md`. Before running, `aws bedrock-agentcore-control create-agent-runtime help` to verify `filesystemConfigurations` is an accepted field.
6. First cloud invoke: `aws bedrock-agentcore invoke-agent-runtime` (check exact subcommand name) with the newest real inbound s3 key. Verify reply lands in S3 + Phoenix/Honeycomb trace.

## Slice after Phase 2: Lambda glue on SES receipt rule

1. Lambda function that: parses SES notification → `mail.source`, `receipt.action.objectKey` → filters by recipient username (agent only fires for `cyndi@cyndibot...`; `pretend-*`, `smoketest-*`, etc. land in S3 but don't invoke) → calls `InvokeAgentRuntime` with `runtimeSessionId = mail.source` and payload `{"s3_key": objectKey}`. Returns fast.
2. Add Lambda action to the existing `cyndibot-inbound` receipt rule, running AFTER the S3 action (S3 is still source-of-truth).
3. End-to-end: pretend-mom → SES → S3 + Lambda → AgentCore → edit + push + reply. No local driver involved.

## After that (in order)
3. AgentCore packaging: Dockerfile, ECR push, `create-agent-runtime` with `filesystemConfigurations.sessionStorage`. Log every command in `infra/README.md`.
4. Lambda wired to the SES receipt rule; Lambda invokes AgentCore. Session id = sender's email.
5. Request SES production access so mom can actually send email to the bot.

## Open questions

- `.env` has no `GITHUB_TOKEN` populated yet. Needs to land before the git tools.
- Do we want a **profile** file for long-lived facts about mom (preferences, spelling quirks), or skip until we see a real need?
- SES sandbox: dev loop is covered by the self-loop trick (send/receive within the verified cyndibot domain). Request production-access before mom goes live — or at minimum verify Jessitron's actual gmail so end-to-end "real mom email in → real reply out" is testable.
