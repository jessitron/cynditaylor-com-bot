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
- `push_site_changes` will fail inside the container — no macOS keychain credential helper. Either set `GITHUB_TOKEN` in `.env` + `git config --global credential.helper store` in the Dockerfile, or in AgentCore proper pull from Secrets Manager on boot. Current smoke test avoids exercising push by using a greeting message.
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

## Slice: Honeycomb-friendly tracing ✅

End-of-session shape: Strands' OTel telemetry now lands in Honeycomb (team `modernity`, env `cynditaylor-com-bot`) as queryable individual columns (`gen_ai.usage.*`, `gen_ai.server.{time_to_first_token,request.duration}`, `gen_ai.tool.*`, `gen_ai.{input,output}.messages` on real spans) instead of an opaque `metadata` JSON blob. Three changes were load-bearing:

1. Removed `openinference-instrumentation-strands-agents` and its `StrandsAgentsToOpenInferenceProcessor`. The processor was bundling unmapped attrs into a single JSON `metadata` column that Honeycomb couldn't query. Phoenix lost its chat-style UI in exchange — acceptable since cloud is the production target. `BedrockInstrumentor` from `openinference-instrumentation-bedrock` stays, since it writes OpenInference attrs natively (no translation phase).
2. Set `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` so Strands emits `gen_ai.input.messages`/`output.messages` JSON arrays (Honeycomb AI view shape) instead of legacy per-message events.
3. Set `LANGFUSE_BASE_URL=langfuse-stub-for-honeycomb` to trip Strands' `is_langfuse` heuristic — substring `"langfuse"` is what matters (the rest is documentation). With the flag tripped, Strands also calls `span.set_attributes(...)` for those JSON arrays alongside `span.add_event(...)`. Without the trip, messages live only on span events; Honeycomb's columnar queries can't reach them.

`scripts/_probe_strands_langfuse.py` — 5-line check that confirms `is_langfuse` and `use_latest_genai_conventions` are both `True` without sending a trace. Useful to flip first when something's wrong.

The full setup (with traps and verification queries) is captured as a Claude Code skill at `notes/skills/strands-honeycomb-tracing/SKILL.md` so other agents can replicate it.

## Next slice: drop the redundant span events

Currently each LLM-call span in Honeycomb has both:
- the JSON-encoded `gen_ai.{input,output}.messages` attrs on the span (good, queryable)
- the `gen_ai.client.inference.operation.details` span events that carry the same payload (redundant — they show up in Honeycomb as separate rows with `name=gen_ai.client.inference.operation.details, duration_ms=0`)

Goal: consolidate. Two sub-questions for this slice:

1. **Cheap version:** custom OTel `SpanProcessor` whose `on_end` walks `span.events`, hoists any unique event-attrs onto the span itself (with a prefix like `event.<event_name>.<attr>` to avoid collisions). Doesn't drop the events; just makes sure no field is event-only.
2. **Full version:** wrap the OTLP exporter so it filters span events out of the serialized payload before send. Events on a `ReadableSpan` are immutable at `on_end` time — must intercept later. The OTLP exporter does its own serialization in `OTLPSpanExporter.export()`; subclass it or wrap it with an exporter-decorator pattern.

Reference points to read in `strands-agents`:
- `strands/telemetry/tracer.py:241` (`_add_event`) — the `to_span_attributes` knob.
- `strands/telemetry/tracer.py:114` (`is_langfuse`) — the heuristic we're tripping.
- All call sites with `to_span_attributes=self.is_langfuse`: lines 357, 417, 472, 563, 660, 766, 842, 864.

Do (1) first, see if Honeycomb is happy without the events being filtered out (they're cheap to ignore in queries — just `WHERE duration_ms > 0`). If event noise is actually hurting, do (2).

## Slice after that: Lambda glue on SES receipt rule

1. Lambda function that: parses SES notification → `mail.source`, `receipt.action.objectKey` → filters by recipient username (agent only fires for `cyndi@cyndibot...`; `pretend-*`, `smoketest-*`, etc. land in S3 but don't invoke) → calls `InvokeAgentRuntime` with `runtimeSessionId = mail.source` and payload `{"s3_key": objectKey}`. Returns fast.
2. Add Lambda action to the existing `cyndibot-inbound` receipt rule, running AFTER the S3 action (S3 is still source-of-truth).
3. End-to-end: pretend-mom → SES → S3 + Lambda → AgentCore → edit + push + reply. No local driver involved.

## Still pending after that

- `GITHUB_TOKEN` in Secrets Manager + container-entrypoint shim. Required before `push_site_changes` works in the cloud.
- Real "edit a file" cloud smoke test (greeting payload only validated the parse+reply path).
- SES production access request so mom can actually send email to the bot.

## Open questions

- `.env` has no `GITHUB_TOKEN` populated yet. Needs to land before the git tools.
- Do we want a **profile** file for long-lived facts about mom (preferences, spelling quirks), or skip until we see a real need?
- SES sandbox: dev loop is covered by the self-loop trick (send/receive within the verified cyndibot domain). Request production-access before mom goes live — or at minimum verify Jessitron's actual gmail so end-to-end "real mom email in → real reply out" is testable.
