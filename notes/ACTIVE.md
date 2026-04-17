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

## After that (in order)

1. More tools:
   - `email.send_reply(to, subject, body, in_reply_to)` — via SES `SendEmail`.
   - `git.ensure_clone(repo_url)` + `git.reset_to_main()`
   - `git.commit_and_push(message)`
   - filesystem tools via `strands-agents-tools` (`file_read`, `file_write`, `shell`)
2. End-to-end dry run: a local driver feeds a real inbound s3 key to the agent, which produces a real commit on `cynditaylor-com` and a reply email to Jessitron (SES sandbox only lets us send to verified addresses).
3. AgentCore packaging: Dockerfile, ECR push, `create-agent-runtime` with `filesystemConfigurations.sessionStorage`. Log every command in `infra/README.md`.
4. Lambda wired to the SES receipt rule; Lambda invokes AgentCore. Session id = sender's email.
5. Request SES production access so mom can actually send email to the bot.

## Open questions

- `.env` has no `GITHUB_TOKEN` populated yet. Needs to land before the git tools.
- Do we want a **profile** file for long-lived facts about mom (preferences, spelling quirks), or skip until we see a real need?
- SES sandbox: for outbound replies, only verified addresses can receive. Jessitron's own email is implicitly verified (it's the account owner), so dev loop works; production-access request happens before mom is live.
