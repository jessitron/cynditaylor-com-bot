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
5. ✅ **Hand-typed roundtrip from Gmail (2026-05-01).** Jessitron sent a real "do the thing!" email from `jessitron@jessitron.com` to `anything@cyndibot.jessitron.honeydemo.io`. Manual driver: `scripts/agent-inbound` (no Lambda yet) processed the newest S3 object, agent recognized it as a non-edit greeting, called `send_reply`. SES accepted, returned message ID. Reply landed in **Gmail Spam**, not Inbox — cyndibot domain has no sender reputation yet. Mail itself is fine; trace via `mcp__phoenix__get-trace` confirmed correct `to`/`subject`/`in_reply_to` headers and `success` status. Validates: full intake → AgentCore-equivalent → outbound reply path with a real human at both ends. **Lambda glue is the only missing piece for hands-off operation.**

## Slice: push to live site (tool only, not yet agent-accessible) ✅

1. ✅ `push_site_changes_impl(remote_branch="main")` shells out to `git push`; the `@tool` wrapper is no-arg and main-only. No `GITHUB_TOKEN` plumbing — relies on the local git credential helper (macOS keychain works out of the box).
2. ✅ `scripts/smoke-push-site` pushes HEAD to `origin/cyndibot-smoke-test`, verifies via `ls-remote`, deletes the branch. Auth path confirmed without touching `main`.
3. ✅ Wired into the agent (commit `b6aff63`): `push_site_changes` is in the tool list in `agent/cyndibot.py`, and the system prompt in step 7 says "Call commit_site_changes, then push_site_changes." A matching changelog convention was seeded so `pretend-`/`smoketest-` senders get `[TEST]`-prefixed entries in `changelog.html`.

## Slice: AgentCore Phase 1 — local container ✅

Goal: a Docker container serving AgentCore's HTTP contract locally, reusing all existing tools. Verify end-to-end before touching AWS. Detailed research notes (HTTP contract, IAM, session filesystem, SDK shape, source URLs) are in `notes/agentcore-contract.md`.

**Outcome:** `cyndibot:local` (126.8 MB, linux/arm64) serves `/ping` + `/invocations`. A greeting-style smoke test goes through the full path: `POST /invocations` → parse_inbound (S3) → Bedrock converse → send_reply (SES) → Phoenix trace under project `cynditaylor-com-bot`.

**Gotchas we hit and fixed (write these down so phase 2 doesn't re-trip them):**
- `.env` uses shell `export KEY="value"` syntax; Docker's `--env-file` rejects `export ` and keeps quotes as literal characters. `scripts/container-run-local` preprocesses `.env` into a docker-compatible temp file (strip `export`, strip surrounding quotes, drop comments/blanks).
- `AWS_PROFILE=sandbox` is exported in Jessitron's shell, not in `.env`. Host scripts inherit it; the container doesn't unless we pass it. `container-run-local` now does `-e AWS_PROFILE="${AWS_PROFILE:-sandbox}"`. For AgentCore proper there's no host shell — the role handles it.
- OTLP endpoint: `.env`'s localhost:6006 points at the container itself, not Phoenix on the host. Dockerfile sets `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://host.docker.internal:6006/v1/traces`, but `--env-file` values override image `ENV`, so we ALSO pass the TRACES var as a late `-e` flag (docker precedence: later `-e` wins).

**Scripts added:**
- `scripts/container-build` — `docker buildx build --platform linux/arm64 --load`.
- `scripts/container-run-local` — foreground `docker run`, creates the `cyndibot-workspace` volume (simulates AgentCore `/mnt/workspace`), mounts `~/.aws:/root/.aws:ro`.
- `scripts/container-wait-ready` — polls `/ping` up to 60s.
- `scripts/container-smoke-ping` — `curl /ping`.
- `scripts/container-smoke-invoke` — stages a greeting-style inbound via `_stage_smoke_greeting.py` (deliberately NOT the newest real inbound, so smoke tests can't accidentally trigger a site edit/push), POSTs to `/invocations`, prints the Phoenix trace URL.

**Pending before Phase 2:**
- ~~`push_site_changes` will fail inside the container~~ ✅ Resolved 2026-05-03 (see "Container `git push` via `GITHUB_TOKEN`" slice below).
- The Dockerfile's `FROM python:3.12-slim` doesn't match the host's `.venv` (Python 3.14.2). `uv sync --frozen` succeeded so the lock is cross-version compatible, but worth remembering when touching deps.

## Slice: AgentCore Phase 2 — ship to AWS ✅ (greeting payload)

**Outcome:** `cyndibot:latest` runs as AgentCore runtime `cyndibot-o2gGSvB6Hz` in us-west-2. End-to-end greeting flow verified: `invoke-agent-runtime` → `parse_inbound` from S3 → Bedrock converse → `send_reply` via SES → trace in Honeycomb team `modernity`, env `cynditaylor-com-bot` (trace_id `6cb81cf8137235c43ac1c2f6ced9f428`, 12 spans, 13.7s).

Done:
1. ECR repo `cyndibot` in us-west-2; `cyndibot:local` pushed to `:latest` (sha256:7a84e51c...).
2. IAM role `CyndibotAgentRuntime` with confused-deputy-safe trust + scoped inline policy. JSON in `infra/iam/`.
3. `scripts/agentcore-create` boots the runtime; `environmentVariables` carry the OTel config (Honeycomb endpoint + ingest key from `.env`), region, and `CYNDIBOT_WORKSPACE`.
4. `scripts/agentcore-wait-ready` polls `get-agent-runtime` until `status=READY`.
5. `scripts/agentcore-smoke-invoke` stages a greeting via `_stage_smoke_greeting.py` and `invoke-agent-runtime`s the runtime.

**Not yet done in Phase 2 (deferred):**
- `GITHUB_TOKEN` in Secrets Manager + container-entrypoint shim. Deferred until we want to exercise `push_site_changes` from the cloud.
- A real "edit a file" cloud smoke test. Greeting payload validates the path; first edit-and-commit invoke will be the next slice.
- SES production access request — still in sandbox, so cyndibot can only reply to verified addresses.

## Slice: `GITHUB_TOKEN` in Secrets Manager (cloud half) ✅ (2026-05-03)

Goal: deployed AgentCore can push without baking the token into environmentVariables (which `get-agent-runtime` returns in plaintext).

1. Secret `cyndibot/github-token` in Secrets Manager (us-west-2). ARN: `arn:aws:secretsmanager:us-west-2:414852377253:secret:cyndibot/github-token-hdaGjb`. `scripts/secret-create-github-token` is the idempotent wrapper (sources `.env` so token never hits shell history; `put-secret-value` if already created).
2. IAM: added `GithubTokenSecret` statement to `cyndibot-agent-runtime-policy.json` granting `secretsmanager:GetSecretValue` on `cyndibot/github-token-*` (the wildcard matches Secrets Manager's random suffix). Applied via the existing `put-role-policy` command in infra/README.md.
3. Container entrypoint extended: if `GITHUB_TOKEN` is unset and `GITHUB_TOKEN_SECRET_ARN` is set, fetch via `python -m agent._fetch_secret` (boto3 only — no awscli baked into image), then proceed with the same git-credential-helper config as before. Locally `.env` provides the token directly so the fetch path is skipped.
4. `_build_agentcore_env_json.py` now requires `GITHUB_TOKEN_SECRET_ARN` and emits it in environmentVariables. The token itself stays out of the runtime config.
5. **Verifying without a real-edit smoke:**
   - Local: `scripts/container-run-local --from-secret` strips `GITHUB_TOKEN` from the env file before docker run, so the entrypoint exercises boto3 against the real Secrets Manager (using mounted `~/.aws` creds). `scripts/container-smoke-push` then pushes to a throwaway branch — green.
   - Cloud: greeting `agentcore-smoke-invoke` after `agentcore-update` returns 200. Because entrypoint runs `set -euo pipefail`, any IAM/fetch failure would prevent the runtime reaching READY, so a healthy boot is sufficient evidence the fetch worked.

A real cloud-side push smoke is still pending — needs `push_site_changes` wired into `agent/inbound.py`.

## Slice: Container `git push` via `GITHUB_TOKEN` ✅ (2026-05-03)

Goal: push from inside the container without depending on the host's macOS keychain. Generalizes to AgentCore: same `GITHUB_TOKEN` env var, sourced from Secrets Manager later instead of `.env`.

1. Fine-grained PAT scoped to `jessitron/cynditaylor-com` only, Contents: Read and write. Lives in `.env` as `GITHUB_TOKEN=...` (already passed through by `container-run-local`'s `.env` preprocessing).
2. `scripts/container-entrypoint`: if `GITHUB_TOKEN` is set, runs `git config --global credential.helper store` and writes `~/.git-credentials` with `https://x-access-token:${GITHUB_TOKEN}@github.com`. No-ops if unset, so the cloud path doesn't break.
3. Dockerfile uses it as `ENTRYPOINT`, with `CMD` still `python -m agent.server`. Required `.dockerignore` exception: `!scripts/container-entrypoint` because `scripts/` is excluded by default.
4. `scripts/container-smoke-push`: `docker cp`s the existing `_smoke_push_site.py` into the running container and runs it (with `PYTHONPATH=/app` since it executes as a script, not `-m`). Pushes to throwaway branch `cyndibot-smoke-test`, verifies, deletes. No live-site impact.

Verified green: full clone → edit → commit → push → cleanup cycle inside `cyndibot:local` using the token.

**Not yet done:**
- `push_site_changes` is still not wired into `agent/inbound.py`. Plan unchanged — watch one manual main-push go through first.
- AgentCore Secrets Manager + container-entrypoint pulls token from there. Same env var name, so no entrypoint changes needed; just IAM + a one-line bootstrap to set `GITHUB_TOKEN` from a secret before exec'ing the server.

## Telemetry work

Tracked separately in `notes/TELEMETRY.md` — Honeycomb-friendly tracing is done; the next telemetry slice (drop redundant span events) lives there. Touch it independently of the agent slices below.

## Slice: Lambda glue on SES receipt rule ✅

1. ✅ Self-contained `lambda/invoke_agent/` module (handler.py + scripts mirroring the `collector/` layout). Idempotent bootstrap/build/deploy/wire-into-ses/smoke/delete.
2. ✅ Receipt rule `cyndibot-inbound` updated to `Actions = [S3Action, LambdaAction]`. LambdaAction is `InvocationType=Event` so SES doesn't wait on the agent's ~30s run.
3. ✅ Recipient filter wired: Lambda only invokes the agent for `cyndi@cyndibot.jessitron.honeydemo.io`. The agent's reply (sent FROM cyndibot@ TO pretend-mom@) re-enters the rule, but the Lambda correctly no-ops on it — no infinite recursion. Confirmed in CloudWatch.
4. ✅ Smoke (`lambda/invoke_agent/scripts/smoke`) sends a real pretend-mom email via SES, polls for the dispatcher's "invoking agent runtime" log line, then waits for the `agentcore response: status=200`. First green run: lambda dispatched in <10s, AgentCore returned 200, agent reply landed in S3 as a separate object.

**`runtimeSessionId` keying decision:** `mom-<sha256(from_header_addr)>`. We use the From header (`mail.commonHeaders.from[0]`), not `mail.source`, because SES rewrites the envelope-from to a per-message bounce mailbox when SES is the originating MTA (i.e. self-loop tests). Real moms emailing from gmail would have a stable `mail.source`; using From makes the session stable in both cases. `_print_session_id.py <addr>` computes the expected id.

**Sender allowlist (added 2026-05-03):** dispatcher hard-codes 4 senders + any `@cyndibot.jessitron.honeydemo.io` (self-domain). Anyone else → `skipped/sender_not_allowed`, no AgentCore invoke. Two smokes in `lambda/invoke_agent/scripts/`:
- `smoke` — real SES roundtrip from `pretend-mom@cyndibot…` (exercises the self-domain rule).
- `smoke-deny` — `aws lambda invoke` with a synthesized SES event from `stranger@example.com` (exercises the deny path).

Not yet covered: a smoke that exercises one of the four explicit allowlist entries with a real external sender. Plan for next session: send a real email from `jessitron@jessitron.com` (already verified for SES outbound, so the agent's reply will deliver back) and watch the lambda log + S3 reply.

**One Honeycomb event per email (added 2026-05-03):** dispatcher now POSTs a single event per invocation to dataset `cyndibot-dispatcher` (env `cynditaylor-com-bot`, team `modernity`) covering every code path — noop / skipped_recipient_filter / skipped_sender_not_allowed / missing_message_id / agent_invoke_failed / invoked. Sent synchronously via the Events API in a `finally` block; failures log a warning but never raise (a raise would trigger SES's async retry, double-invoking AgentCore on success). Field naming uses `dispatcher.*`, `email.*`, and OTel-standard `session.id` / `aws.s3.key` / `faas.invocation_id` / `faas.name` to keep room for the agent's spans to stamp the same column names later. Verified via `smoke-deny`: event_id round-trips from the Lambda log into Honeycomb. Cross-dataset join is now wired — see `notes/TELEMETRY.md` "Done: stamp `session.id` on every agent span".

**SES verification status (as of 2026-05-03):**
- Verified for outbound replies: `cyndibot.jessitron.honeydemo.io` (domain), `jessitron@jessitron.com`.
- Verification email sent, awaiting click: `taylor777@sbcglobal.net` (mom).
- Not yet requested: `jessitron@gmail.com`, `mamacatitron@gmail.com`. Send via `scripts/ses-verify-email <addr>` whenever wanted; recipient must click the link in the verification mail.

## Still pending

- Real "edit a file" cloud smoke test (greeting payload only validated the parse+reply path; the lambda smoke is also greeting-style). Will exercise the Secrets Manager fetch through to an actual `git push` in the cloud.
- SES production access request so mom can actually send email to the bot.
- **Unreplyable-recipient error visibility.** When the agent tries to `send_reply` to an address SES can't deliver to (sandbox: unverified identity; prod: hard bounce), the current tool returns `success` as long as the SES API call returns a Message-ID — silent failure from the agent's POV. Test by sending an inbound from an unverified address, then verify we surface the failure somewhere actionable (SES bounce SNS topic? agent-side preflight check against verified identities? a "delivery failed" reply to a fallback address?). Discovered when the first real-mom-style email landed in Gmail spam — different failure mode but same observability gap.

## Open questions

- `.env` has no `GITHUB_TOKEN` populated yet. Needs to land before the git tools.
- Do we want a **profile** file for long-lived facts about mom (preferences, spelling quirks), or skip until we see a real need?
- SES sandbox: dev loop is covered by the self-loop trick (send/receive within the verified cyndibot domain). Request production-access before mom goes live — or at minimum verify Jessitron's actual gmail so end-to-end "real mom email in → real reply out" is testable.
