# Active plan

## Decisions locked in so far

- **AWS account:** jessitron-sandbox (`414852377253`), region `us-west-2`.
- **Model:** Claude Sonnet 4.5 via Bedrock inference profile `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. Must use inference-profile IDs, not bare model IDs.
- **Repo strategy:** clone `cynditaylor-com` into AgentCore session storage at `/mnt/workspace/cynditaylor-com`, commit via shelled `git`. Reset to `origin/main` at start of each invoke.
- **Session model:** one AgentCore `runtimeSessionId` per mom's email address. 14-day idle TTL is plenty.
- **Conversation memory:** no new store. Inbound SES message (landing in S3) + SES sent-log + git log on the site repo are authoritative. Strands `FileSessionManager` in session storage is convenience, not source of truth.
- **Observability:** OTel → Arize Phoenix (self-hosted locally, `http://localhost:6006/v1/traces`). `.env` is now pointed at Phoenix. Honeycomb may come later.
- **Build tooling:** `uv`.
- **Site repo:** `github.com/jessitron/cynditaylor-com` (confirmed to exist).

## Done so far

1. `pyproject.toml` + `uv`, `agent/hello.py` confirms Bedrock auth from Python.
2. OTel → Phoenix wired; Bedrock auto-instrumented via `openinference-instrumentation-bedrock`.
3. `hello.py` converted to a Strands Agent (no tools); 4-span traces land in Phoenix with correct OpenInference kinds (agent → chain → llm → chain).
4. Twilio send API smoke-tested, then **abandoned** — US toll-free and 10DLC both require A2P verification paperwork that's not worth it for a 1:1 bot.

## Pivot: SMS → SES email

Mom emails the bot instead of texting it. Drastically less carrier-compliance hassle. Scripts and notes from the Twilio detour are kept in git history for reference.

## Next slice: email intake proof

1. Decide the receiving address (see open questions). Verify the domain in SES (us-west-2).
2. Create an SES receipt rule that stores inbound messages in an S3 bucket (later: invoke Lambda directly).
3. From mom's email, send a test message; confirm the raw MIME lands in S3.
4. Script: `scripts/ses-list-recent` that fetches the latest S3 object(s) and prints subject/from/body.

## After that (in order)

1. Tools for the agent:
   - `email.parse_inbound(s3_key)` — pull the MIME from S3, return structured fields.
   - `email.send_reply(to, subject, body, in_reply_to)` — via SES `SendEmail`.
   - `git.ensure_clone(repo_url)` + `git.reset_to_main()`
   - `git.commit_and_push(message)`
   - filesystem tools via `strands-agents-tools` (`file_read`, `file_write`, `shell`)
2. End-to-end dry run: a local script feeds a fake inbound message to the agent, which produces a real commit on `cynditaylor-com` and a reply email (sandbox: to Jessitron only).
3. AgentCore packaging: Dockerfile, ECR push, `create-agent-runtime` with `filesystemConfigurations.sessionStorage`. Log every command in `infra/README.md`.
4. Lambda wired to SES receipt rule; Lambda invokes AgentCore. Session id = sender's email.
5. Request SES production access so mom (and anyone else) can actually send email to the bot.

## Open questions

- **Receiving address:** `bot@cynditaylor.com`? `edits@cynditaylor.com`? Requires MX records for that domain (or subdomain) to point at SES. The domain's A/CNAME for GitHub Pages is independent of MX, so no conflict with the live site.
- `.env` has no `GITHUB_TOKEN` populated yet. Needs to land before the git tools.
- Do we want a **profile** file for long-lived facts about mom (preferences, spelling quirks), or skip until we see a real need?
