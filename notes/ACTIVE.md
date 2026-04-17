# Active plan

## Decisions locked in so far

- **AWS account:** jessitron-sandbox (`414852377253`), region `us-west-2`.
- **Model:** Claude Sonnet 4.5 via Bedrock inference profile `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. Must use inference-profile IDs, not bare model IDs.
- **Repo strategy:** clone `cynditaylor-com` into AgentCore session storage at `/mnt/workspace/cynditaylor-com`, commit via shelled `git`. Reset to `origin/main` at start of each invoke.
- **Session model:** one AgentCore `runtimeSessionId` per mom's phone number. 14-day idle TTL is plenty.
- **Conversation memory:** no new store. Twilio Messages API (400-day retention) + git log on the site repo are authoritative. Strands `FileSessionManager` in session storage is convenience, not source of truth.
- **Observability:** OTel → Arize Phoenix (self-hosted locally, `http://localhost:6006/v1/traces`). `.env` is now pointed at Phoenix. Honeycomb may come later.
- **Build tooling:** `uv`.
- **Site repo:** `github.com/jessitron/cynditaylor-com` (confirmed to exist).

## Next slice: local Bedrock hello-world

Smallest first step that doesn't pretend to be AgentCore yet.

1. `pyproject.toml` + `uv` (or pip) with `boto3`.
2. `agent/hello.py` — calls Sonnet 4.5 via `bedrock-runtime` in Python. Just prints the response.
3. Confirm auth works from code, not just CLI.

## After that (in order)

1. Wire OTel → Phoenix (self-hosted locally) in Python; confirm a span lands at `localhost:6006`.
2. Convert `hello.py` to a Strands Agent with no tools; confirm traces still flow.
3. Add tools one at a time:
   - `twilio.get_recent_messages(phone_number, limit)`
   - `twilio.send_sms(phone_number, body)`
   - `git.ensure_clone(repo_url)` + `git.reset_to_main()`
   - `git.commit_and_push(message)`
   - filesystem tools via `strands-agents-tools` (`file_read`, `file_write`, `shell`)
4. End-to-end dry run: `python -m agent "change the phone number in index.html to 555-1234"` produces a real commit on `cynditaylor-com`.
5. AgentCore packaging: Dockerfile, ECR push, `create-agent-runtime` with `filesystemConfigurations.sessionStorage`. Log every command in `infra/README.md`.
6. Lambda webhook for Twilio, session id = phone number.

## Open questions

- `.env` has no `GITHUB_TOKEN` or `TWILIO_*` populated yet. These need to land before step 3.
- Do we want a **profile** file for long-lived facts about mom (preferences, spelling quirks), or skip until we see a real need?
