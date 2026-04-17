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

## After that (in order)
3. AgentCore packaging: Dockerfile, ECR push, `create-agent-runtime` with `filesystemConfigurations.sessionStorage`. Log every command in `infra/README.md`.
4. Lambda wired to the SES receipt rule; Lambda invokes AgentCore. Session id = sender's email.
5. Request SES production access so mom can actually send email to the bot.

## Open questions

- `.env` has no `GITHUB_TOKEN` populated yet. Needs to land before the git tools.
- Do we want a **profile** file for long-lived facts about mom (preferences, spelling quirks), or skip until we see a real need?
- SES sandbox: dev loop is covered by the self-loop trick (send/receive within the verified cyndibot domain). Request production-access before mom goes live — or at minimum verify Jessitron's actual gmail so end-to-end "real mom email in → real reply out" is testable.
