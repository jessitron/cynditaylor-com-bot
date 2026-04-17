# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repo is in a **pre-implementation** state. The README describes what we want to build, not what exists. There is no source code, no `requirements.txt`, no `agent/`, no `lambda/`, and no `infra/` directory yet. When asked to "run" or "test" something, first check whether the thing even exists — don't assume the layout in the README is real.

Previous commit history shows earlier attempts were cleared out (`9c4f1e0 Clear it out, start again`). Treat this as a fresh start.

## What we're building

An agent that lets Jessitron's mom update her static HTML GitHub Pages site (`cynditaylor-com`) by sending SMS messages. The planned pipeline: Twilio SMS → AWS Lambda webhook → AWS AgentCore → Strands Agent (tools: GitHub read/write, Twilio reply) → commit to the site repo → GitHub Pages deploys → SMS confirmation back to mom. Observability via OpenTelemetry → Arize Phoenix.

The target site repo (`cynditaylor-com/`) is gitignored — if it appears locally it's a sibling checkout, not part of this repo.

See README.md for the full architecture and the rationale in "Key decisions" (Strands for AWS-native + OTel, direct GitHub API over git clone, no confirmation step because the site is low-risk, Phoenix for OTel-native trace inspection).

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
- Setting up infra via `awscli` is fine. **CRUCIAL:** every AWS command that changes state must be recorded in `infra/README.md` so the setup is reproducible. Create that file if it doesn't exist.
