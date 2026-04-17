# Active plan

## Goal: first vertical slice, runnable locally

A single Python entry point that:
1. Takes a text instruction as an argument (e.g. `"Change the phone number in the contact section to 555-1234"`)
2. Uses a **Strands Agent** backed by **Bedrock Sonnet 4.5**
3. Has two tools: `read_file` and `write_and_commit` against the `cynditaylor-com` repo via the GitHub Contents API
4. Emits **OTel traces to Honeycomb** (`.env` is already configured for this)

No Twilio, no Lambda, no AgentCore deploy. Those come later.

## Steps (smallest-first)

1. **Skeleton + Bedrock hello-world** — `agent/hello.py` calls Sonnet 4.5 via `boto3` directly, confirms Python-side auth works. `pyproject.toml` + `uv`.
2. **OTel wiring** — add OpenTelemetry + `openinference-instrumentation-bedrock`, confirm a span lands in Honeycomb.
3. **Strands agent, no tools** — convert hello-world into a Strands Agent with just a system prompt. Confirm traces still flow.
4. **GitHub tools** — add `read_file` + `write_and_commit` using `PyGithub` or raw Contents API. Needs `GITHUB_TOKEN` in `.env`.
5. **End-to-end dry run** — `python -m agent "make a trivial change to index.html"` produces a real commit on `cynditaylor-com`.

## Open questions / blockers

- `.env` currently has only OTel vars. `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`, `GITHUB_BRANCH` need to be added before step 4.
- The target site repo `cynditaylor-com` — does it actually exist on GitHub? Need to confirm the owner/name before step 4.
- Build tooling: `pip` vs `uv`? Defaulting to `uv` unless corrected.
