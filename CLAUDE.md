# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

In progress, partially built. **`notes/ACTIVE.md` is the source of truth for what exists vs. what's planned** — read it before assuming anything about layout or current state. Telemetry work (OTel shape into Honeycomb) is a separate line of work tracked in **`notes/TELEMETRY.md`**.

Built: local Strands agent (`agent/cyndibot.py`, `agent/inbound.py`), full OTel → Honeycomb in both local and cloud (local via an `otel-collector-contrib` container started by `./run`; cloud via the Boswell collector lambda in `collector/`), SES inbound + outbound end-to-end on `cyndibot.jessitron.honeydemo.io`, site-edit tools (`agent/tools/site_tools.py`) with clone/sync/read/write/delete/commit/push, image tools (`agent/tools/image_tools.py` + `agent/image_subagent.py`) for viewing/inspecting/rotating/resizing attachments, AgentCore runtime deployed (`cyndibot-o2gGSvB6Hz` in us-west-2), `GITHUB_TOKEN` in Secrets Manager (fetched by container at startup), SES → Lambda → AgentCore dispatcher (`lambda/invoke_agent/`) wired into the `cyndibot-inbound` receipt rule, local container parity. The full pipeline runs end-to-end in cloud.

Not yet built: SES production-access (still in sandbox — outbound replies only go to verified addresses).

## What we're building

An agent that lets Jessitron's mom update her static HTML GitHub Pages site (`cynditaylor-com`) by **sending email**. Pipeline: mom emails `*@cyndibot.jessitron.honeydemo.io` → Amazon SES inbound → S3 (raw MIME, source of truth) → dispatcher Lambda (`lambda/invoke_agent/`) → AWS AgentCore Runtime → Strands Agent (tools: `parse_inbound`, `send_reply`, `sync_workspace`, `list_site_files`, `read_site_file`, `write_site_file`, `delete_site_file`, `view_site_image`, `image_info`, `edit_images` subagent, `commit_site_changes`, `push_site_changes`) → commit + push to the site repo → GitHub Pages deploys → SES `SendEmail` reply back to mom. Observability via OpenTelemetry → Honeycomb in both environments — locally through an `otel-collector-contrib` container started by `./run`; in cloud through the Boswell collector lambda.

> **Why email, not SMS?** Earlier plan used Twilio SMS. US toll-free A2P / 10DLC carrier compliance was disproportionate for a 1:1 bot, so we pivoted to SES. **Don't add new Twilio code.**

The target site repo (`cynditaylor-com/`) is gitignored — if it appears locally it's the agent's working clone (or a sibling checkout), not part of this repo.

See README.md for the full architecture and the rationale in "Key decisions" (Strands for AWS-native + OTel, clone-into-session-storage over direct GitHub API, no confirmation step because the site is low-risk, Honeycomb everywhere via a small local collector + Boswell in cloud).

## Components

- `agent/` — Strands agent. **Build/run/deploy/smoke scripts in `agent/README.md`.**
- `lambda/invoke_agent/` — SES → Lambda → AgentCore dispatcher. Deploy/smoke scripts under `lambda/invoke_agent/scripts/`; setup steps in `infra/README.md`.
- `collector/` — Boswell OTel collector lambda. See `collector/README.md`.
- `infra/README.md` — one-time AWS setup commands (SES, Route 53, S3, IAM) and reproducible state-changes log.

## Working conventions (from `.augment-guidelines`)

- **Plans and summaries go in `notes/ACTIVE.md`**, not in chat output. Create `notes/` if it doesn't exist.
- **Do not write tests** unless explicitly asked.
- **No fallbacks on failure** — raise a clear error instead.
- **No comments for obvious things.** If a method has no docstring, don't add one.

## Environment

- Python 3.11+ target (devcontainer uses 3.12).
- Secrets live in `.env` (gitignored and already populated locally); see README for the variable list.

## AWS

- Use the **jessitron-sandbox** account, ID **414852377253**. Verify with `aws sts get-caller-identity` before running AWS commands.
- Region: **us-west-2** (Bedrock model access confirmed here).
- Setting up infra via `awscli` is fine. **CRUCIAL:** every AWS command that changes state must be recorded in `infra/README.md` so the setup is reproducible. Create that file if it doesn't exist.
- `awscli` must be **≥2.30** to get the `bedrock-runtime converse` subcommand. Installed via asdf.

## Bedrock

- Default model: **Claude Sonnet 4.5**, inference-profile ID `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. Bump to Opus (`us.anthropic.claude-opus-4-7`) only when Sonnet isn't enough.
- **Gotcha:** the bare model ID (e.g. `anthropic.claude-sonnet-4-5-20250929-v1:0`) fails with "on-demand throughput isn't supported." Always use the cross-region inference-profile ID (prefixed `us.` or `global.`). List them with `aws bedrock list-inference-profiles --region us-west-2`.

## Observability

Tracked as a separate line of work in **`notes/TELEMETRY.md`** — current shape, what's done, what's next. Two load-bearing rules to repeat here:

- **After any test run that emits traces, report the trace URL** so Jessitron can click through. Use the Honeycomb MCP to find the trace and surface a permalink. Local traces land in team `modernity`, env `local`; cloud traces in env `cynditaylor-com-bot`.
- Local collector runs in docker (`http://localhost:4318/v1/traces`, started by `./run`, config in `collector/config.local.yaml`) and forwards to Honeycomb. All OTel env vars live in the gitignored `.env`.

There's also `collector/` — an OTel collector deployed as a Lambda ("Boswell") that post-processes traces between AgentCore and Honeycomb. See `collector/README.md`.

## Skills in this repo

Self-contained skill docs in `notes/skills/<name>/SKILL.md`. Read the matching one before doing similar work in this or another project:

- `strands-honeycomb-tracing` — Strands Agent OTel setup that lands queryable columns in Honeycomb's AI view.
- `otel-collector-on-lambda` — packaging the OTel Collector as a Lambda container image. Six gotchas paid in blood.
- `collector-pipeline-provenance` — three-attribute pattern (`collector.<name>`, `.version`, `.invocation_id`) for stamping spans with which collector processed them.
