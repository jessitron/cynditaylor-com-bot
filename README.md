# Artist Website Update Agent

An AI agent that updates a static HTML GitHub Pages site based on SMS messages. Built with Strands Agents on AWS AgentCore, instrumented with Arize Phoenix via OpenTelemetry.

## Status: Hypothetical

This README describes what we want this project to be, not what it is.

## What it does

1. Mom sends a text message describing a change she wants on her website
2. Twilio receives the SMS and forwards it to an AWS Lambda webhook
3. Lambda invokes the agent on AgentCore, using mom's phone number as the session ID
4. The agent pulls recent messages from Twilio for context, finds and edits the relevant files in its cloned workspace, and commits + pushes
5. GitHub Pages deploys automatically
6. Agent replies to mom via SMS confirming the change (or asking for clarification)

## Architecture

```
Mom's phone
    │ SMS
    ▼
Twilio ────────────────────────┐ (also the conversation log we read from)
    │ webhook (HTTP POST)      │
    ▼                          │
AWS Lambda  (entry point)      │
    │ invokes                  │
    ▼                          │
AWS AgentCore Runtime          │
  (one session per phone #,    │
   persistent /mnt/workspace)  │
    │                          │
    ├── Strands Agent  ◄───────┘ (reads recent Twilio msgs at start of invoke)
    │       ├── cloned site repo at /mnt/workspace/cynditaylor-com
    │       ├── tool: read/edit/grep (filesystem)
    │       ├── tool: commit + push (shelled git)
    │       └── tool: send_sms (Twilio)
    │
    └── OpenTelemetry → Arize Phoenix  (observability)
```

| Concern | Choice |
|---|---|
| Agent framework | [Strands Agents](https://strandsagents.com/) |
| Agent runtime | [AWS AgentCore Runtime](https://aws.amazon.com/bedrock/agentcore/) with persistent session storage |
| LLM | Claude Sonnet 4.5 via Amazon Bedrock (region us-west-2) |
| SMS + conversation log | [Twilio](https://www.twilio.com/) (Messages API, 400-day retention) |
| Webhook entry point | AWS Lambda |
| Site hosting | GitHub Pages (static HTML) |
| Site source | GitHub repo — cloned into AgentCore session storage, committed via shelled `git` |
| Observability | [Arize Phoenix](https://phoenix.arize.com/) via OpenTelemetry + OpenInference |

## Project structure

```
cynditaylor-com-bot/
├── README.md
├── agent/
│   ├── agent.py          # Strands agent definition, system prompt, tool wiring
│   ├── tools/
│   │   ├── git.py        # clone / reset / commit / push against the cloned workspace
│   │   └── twilio.py     # get_recent_messages, send_sms
│   └── entrypoint.py     # BedrockAgentCoreApp wrapper
├── lambda/
│   └── handler.py        # Twilio webhook → AgentCore invocation (session id = phone #)
├── infra/
│   └── README.md         # running log of AWS setup commands
├── Dockerfile            # for AgentCore Runtime container
├── pyproject.toml
└── .env.example
```

## Environment variables

```
# AWS
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
MOM_PHONE_NUMBER=

# GitHub
GITHUB_TOKEN=           # fine-grained PAT with Contents: read+write on the site repo
GITHUB_REPO_OWNER=jessitron
GITHUB_REPO_NAME=cynditaylor-com
GITHUB_BRANCH=main

# Arize Phoenix (OpenTelemetry)
PHOENIX_API_KEY=        # leave empty if self-hosting
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
```

## Getting started

### Prerequisites

- Python 3.11+
- AWS account with Bedrock access (Claude model enabled in us-west-2)
- Twilio account
- GitHub fine-grained personal access token with Contents: read+write on the site repo
- Docker (for AgentCore deployment)
- Arize Phoenix running locally: `docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest`

### Local development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in env vars
cp .env.example .env

# Run the agent directly (no AgentCore, no Twilio)
python agent/agent.py "Change the phone number in the contact section to 555-1234"
```

Traces will appear in Phoenix at http://localhost:6006.

### Deploy to AgentCore

```bash
# Build and push container
docker build -t mom-site-agent .
# (push to ECR, deploy via AgentCore Runtime — see infra/)
```

### Wire up Twilio

1. Deploy the Lambda webhook (`lambda/handler.py`)
2. In Twilio console, set the SMS webhook URL for mom's number to the Lambda URL
3. Make sure the Lambda has permission to invoke the AgentCore endpoint

## Observability

Traces are instrumented via `openinference-instrumentation-bedrock` and sent to Phoenix via OTLP. Every agent run produces a trace showing:
- The incoming SMS text
- The recent Twilio conversation history pulled in as context
- Which files were read / edited in the cloned repo
- The LLM's reasoning and edits
- The commit that was pushed
- The SMS reply sent

View traces at http://localhost:6006 (local Phoenix) or your hosted Phoenix instance.

## Key decisions

**Why Strands?** AWS-native, minimal boilerplate, built-in OTel support, and first-class AgentCore integration. Agent logic stays simple: system prompt + tools, no graph definition needed.

**Why clone the repo onto AgentCore session storage (not direct GitHub API)?** AgentCore Runtime gives each session a persistent Linux filesystem (preview feature, up to 1 GB, 14-day idle TTL). Cloning the site repo once and keeping it warm lets the agent use normal tools — `grep`, `sed`, multi-file edits, a local preview if we want one — instead of making round-trips for every file. A scoped PAT handles auth the same way the Contents API would. Working tree is reset to `origin/main` at the start of every invoke so state bugs can't accumulate.

**Why one AgentCore session per mom's phone number?** When mom texts a follow-up ("no wait, make it horizontal"), we want the agent to know what "it" refers to. Same `sessionId` = same microVM = warm clone + `FileSessionManager` conversation history. 14-day idle TTL is far longer than any realistic gap between texts.

**Where does conversation memory live?** Three systems that are already authoritative — the agent just reads them, it doesn't maintain a parallel store:
- **Twilio Messages API** — every SMS exchanged, both directions, 400-day default retention. Agent pulls recent messages for mom's number at the start of each invoke. Captures failed-reply cases that never made it to a commit.
- **Site repo git log** — what actually changed. Rich commit messages ("Mom asked for larger font in bio section; changed `h2` size from 18px → 22px in `style.css`") make this useful as reasoning history, not just a changelog.
- **Session storage** (`/mnt/workspace/.sessions/`) — Strands `FileSessionManager` keeps the running conversation. Convenient but not authoritative; Twilio + git are the sources of truth.

Long-lived facts about mom (preferences, spelling quirks) that don't belong in either system can live in a small profile file in this repo — that's a **profile**, distinct from conversation memory.

**Why no confirmation step?** The site is low-risk. The agent makes the change, pushes it, and texts mom a confirmation. If something's wrong, she texts again — and the next invoke has the full Twilio thread as context.

**Why Arize Phoenix?** OTel-native, open source, self-hostable, and specifically good at the "what did the agent actually do" question — not just eval scores. Start here; we can add Honeycomb later if we want hosted/long-term storage.
