# Artist Website Update Agent

An AI agent that updates a static HTML GitHub Pages site based on email messages. Built with Strands Agents on AWS AgentCore, instrumented with Arize Phoenix via OpenTelemetry.

## Status: In progress

This README describes the shape of the project. Some pieces are built (local Strands agent, full OTel → Phoenix, SES inbound pipeline end-to-end), some aren't (agent tools, Lambda, AgentCore deploy). See `notes/ACTIVE.md` for current state and `infra/README.md` for reproducible AWS setup.

## What it does

1. Mom sends an email describing a change she wants on her website, to `cyndibot.jessitron.honeydemo.io`.
2. Amazon SES receives the email and stores the raw MIME in S3 (and later: fires a Lambda).
3. Lambda invokes the agent on AgentCore, using mom's email address as the session ID.
4. The agent reads the inbound MIME, finds and edits the relevant files in its cloned workspace, and commits + pushes.
5. GitHub Pages deploys automatically.
6. Agent replies to mom via SES confirming the change (or asking for clarification).

> **Why email and not SMS?** The original plan used Twilio SMS. US toll-free A2P verification and 10DLC registration would have been weeks of carrier-compliance paperwork for a 1:1 bot. Email via SES has essentially none of that — the only gate is SES sandbox mode (lifted with a click once we're ready for mom).

## Architecture

```
Mom's email client
    │ email
    ▼
Amazon SES  (inbound)
    │ receipt rule
    ▼
S3 bucket  (raw MIME, persistent)
    │
    ▼                          ┌─ reply email → Amazon SES (outbound) → mom
AWS Lambda  (entry point)      │
    │ invokes                  │
    ▼                          │
AWS AgentCore Runtime          │
  (one session per email,      │
   persistent /mnt/workspace)  │
    │                          │
    ├── Strands Agent ─────────┘
    │       ├── cloned site repo at /mnt/workspace/cynditaylor-com
    │       ├── tool: email.parse_inbound (read MIME from S3)
    │       ├── tool: email.send_reply    (SES SendEmail)
    │       ├── tool: read/edit/grep      (filesystem)
    │       └── tool: commit + push       (shelled git)
    │
    └── OpenTelemetry → Arize Phoenix  (observability)
```

| Concern | Choice |
|---|---|
| Agent framework | [Strands Agents](https://strandsagents.com/) |
| Agent runtime | [AWS AgentCore Runtime](https://aws.amazon.com/bedrock/agentcore/) with persistent session storage |
| LLM | Claude Sonnet 4.5 via Amazon Bedrock (region us-west-2) |
| Email in | Amazon SES inbound → S3 (`cyndibot-incoming-emails`) |
| Email out | Amazon SES `SendEmail` |
| Receiving address | `*@cyndibot.jessitron.honeydemo.io` |
| Webhook entry point | AWS Lambda (triggered by SES receipt rule) |
| Site hosting | GitHub Pages (static HTML) |
| Site source | GitHub repo — cloned into AgentCore session storage, committed via shelled `git` |
| Observability | [Arize Phoenix](https://phoenix.arize.com/) via OpenTelemetry + OpenInference |

## Project structure

```
cynditaylor-com-bot/
├── README.md
├── agent/
│   ├── hello.py          # minimal Strands Agent, smoke test (Sonnet 4.5)
│   ├── observability.py  # TracerProvider + OpenInference instrumentors
│   └── tools/            # (planned) email, git, filesystem
├── lambda/               # (planned) SES → AgentCore invocation
├── infra/
│   └── README.md         # running log of every AWS setup command
├── scripts/              # run, check, SES, Route 53, S3, agent invokers, AgentCore deploy
├── Dockerfile            # (planned) AgentCore Runtime container
├── pyproject.toml
├── notes/ACTIVE.md       # plan and state of play
└── .env.example
```

## Environment variables

```
# AWS
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# SES
SES_INBOUND_BUCKET=cyndibot-incoming-emails
SES_INBOUND_PREFIX=emails/
SES_FROM_ADDRESS=bot@cyndibot.jessitron.honeydemo.io

# GitHub
GITHUB_TOKEN=           # fine-grained PAT with Contents: read+write on the site repo
GITHUB_REPO_OWNER=jessitron
GITHUB_REPO_NAME=cynditaylor-com
GITHUB_BRANCH=main

# OpenTelemetry → Phoenix
OTEL_SERVICE_NAME=cynditaylor-com-bot
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:6006/v1/traces
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

## Getting started

### Prerequisites

- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- AWS account with Bedrock access (Claude Sonnet 4.5 enabled in us-west-2) and SES in the same region
- GitHub fine-grained personal access token with Contents: read+write on the site repo
- Docker (for local Phoenix and later AgentCore deployment)

### Local development

```bash
# Start Phoenix (idempotent; leaves it running in the background)
./run

# Copy and fill in env vars
cp .env.example .env

# Smoke-test the Strands agent against Bedrock
./scripts/hello

# Check that traces are landing in Phoenix
./scripts/check-last-trace
```

Phoenix UI: http://localhost:6006.

### SES plumbing (one-time)

Reproducible via `scripts/ses-*` and `scripts/route53-*`; every state-changing command is logged in `infra/README.md`.

### Deploy to AgentCore

_Not built yet._ Plan: `docker build` → push to ECR → `create-agent-runtime` with `filesystemConfigurations.sessionStorage`. See `notes/ACTIVE.md`.

### Wire up SES to Lambda

_Not built yet._ Plan: replace the S3 action in the `cyndibot-inbound` receipt rule with a Lambda action that invokes the AgentCore runtime with `sessionId = sender's email`.

## Observability

Traces are instrumented via `openinference-instrumentation-bedrock` and `openinference-instrumentation-strands-agents` (a span processor that converts Strands' native OTel GenAI spans into OpenInference conventions). Sent to Phoenix via OTLP. Every agent run shows:
- The incoming email's parsed fields
- Which files were read / edited in the cloned repo
- The LLM's reasoning and edits
- The commit that was pushed
- The SMTP send of the reply

View traces at http://localhost:6006.

## Key decisions

**Why Strands?** AWS-native, minimal boilerplate, built-in OTel support, and first-class AgentCore integration. Agent logic stays simple: system prompt + tools, no graph definition needed.

**Why clone the repo onto AgentCore session storage (not direct GitHub API)?** AgentCore Runtime gives each session a persistent Linux filesystem (up to 1 GB, 14-day idle TTL). Cloning the site repo once and keeping it warm lets the agent use normal tools — `grep`, `sed`, multi-file edits, a local preview if we want one — instead of making round-trips for every file. A scoped PAT handles auth the same way the Contents API would. Working tree is reset to `origin/main` at the start of every invoke so state bugs can't accumulate.

**Why one AgentCore session per mom's email address?** When mom sends a follow-up ("no wait, make it horizontal"), we want the agent to know what "it" refers to. Same `sessionId` = same microVM = warm clone + `FileSessionManager` conversation history. 14-day idle TTL is far longer than any realistic gap between messages.

**Where does conversation memory live?** Three systems that are already authoritative — the agent just reads them, it doesn't maintain a parallel store:
- **S3 inbound bucket** — raw MIME of every email mom has sent, forever (our retention). Agent reads recent ones at the start of each invoke for context.
- **Site repo git log** — what actually changed. Rich commit messages ("Mom asked for larger font in bio section; changed `h2` size from 18px → 22px in `style.css`") make this useful as reasoning history, not just a changelog.
- **Session storage** (`/mnt/workspace/.sessions/`) — Strands `FileSessionManager` keeps the running conversation. Convenient but not authoritative; S3 + git are the sources of truth.

Outbound replies aren't recorded by SES by default; the `email.send_reply` tool will write a copy of each sent message to S3 as it sends, so the conversation is fully reconstructable without touching the agent's session state.

Long-lived facts about mom (preferences, spelling quirks) that don't belong in either system can live in a small profile file in this repo — that's a **profile**, distinct from conversation memory.

**Why no confirmation step?** The site is low-risk. The agent makes the change, pushes it, and emails mom a confirmation. If something's wrong, she replies — and the next invoke has the full email thread as context.

**Why Arize Phoenix?** OTel-native, open source, self-hostable, and specifically good at the "what did the agent actually do" question — not just eval scores. Start here; we can add Honeycomb later if we want hosted/long-term storage.
