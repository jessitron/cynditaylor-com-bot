# Artist Website Update Agent

An AI agent that updates a static HTML GitHub Pages site based on SMS messages. Built with Strands Agents on AWS AgentCore, instrumented with Arize Phoenix via OpenTelemetry.

## Status: Hypothetical

This README describes what we want this project to be, not what it is.

## What it does

1. Mom sends a text message describing a change she wants on her website
2. Twilio receives the SMS and forwards it to an AWS Lambda webhook
3. Lambda invokes the agent on AgentCore
4. The agent reads the relevant HTML file from GitHub, makes the edit, and commits + pushes
5. GitHub Pages deploys automatically
6. Agent replies to mom via SMS confirming the change

## Architecture

```
Mom's phone
    │ SMS
    ▼
Twilio
    │ webhook (HTTP POST)
    ▼
AWS Lambda  (entry point)
    │ invokes
    ▼
AWS AgentCore Runtime  (hosts the agent)
    │
    ├── Strands Agent
    │       ├── tool: read_file (GitHub API)
    │       ├── tool: write_and_commit (GitHub API)
    │       └── tool: send_sms (Twilio)
    │
    └── OpenTelemetry → Arize Phoenix  (observability)
```

| Concern | Choice |
|---|---|
| Agent framework | [Strands Agents](https://strandsagents.com/) |
| Agent runtime | [AWS AgentCore](https://aws.amazon.com/bedrock/agentcore/) |
| LLM | Claude via Amazon Bedrock |
| SMS | [Twilio](https://www.twilio.com/) |
| Webhook entry point | AWS Lambda |
| Site hosting | GitHub Pages (static HTML) |
| Site source | GitHub repo (direct API commits) |
| Observability | [Arize Phoenix](https://phoenix.arize.com/) via OpenTelemetry + OpenInference |

## Project structure

```
mom-site-agent/
├── README.md
├── agent/
│   ├── agent.py          # Strands agent definition, system prompt, tool wiring
│   ├── tools/
│   │   ├── github.py     # read_file, write_and_commit tools
│   │   └── sms.py        # send_sms tool (Twilio)
│   └── entrypoint.py     # BedrockAgentCoreApp wrapper
├── lambda/
│   └── handler.py        # Twilio webhook → AgentCore invocation
├── infra/                # CDK or Terraform (TBD)
├── Dockerfile            # for AgentCore Runtime container
├── requirements.txt
└── .env.example
```

## Environment variables

```
# AWS
AWS_REGION=

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
MOM_PHONE_NUMBER=

# GitHub
GITHUB_TOKEN=           # fine-grained PAT with Contents: read+write on the site repo
GITHUB_REPO_OWNER=jessitron
GITHUB_REPO_NAME=cynditaylor-com-bot
GITHUB_BRANCH=main

# Arize Phoenix
PHOENIX_API_KEY=        # leave empty if self-hosting
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
```

## Getting started

### Prerequisites

- Python 3.11+
- AWS account with Bedrock access (Claude model enabled)
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

Traces are instrumented via `openinference-instrumentation-bedrock`. Every agent run produces a trace showing:
- The incoming SMS text
- Which files were read from GitHub
- The LLM's reasoning and edits
- The commit that was pushed
- The SMS reply sent

View traces at http://localhost:6006 (local Phoenix) or your hosted Phoenix instance.

## Key decisions

**Why Strands?** AWS-native, minimal boilerplate, built-in OTel support, and first-class AgentCore integration. Agent logic stays simple: system prompt + tools, no graph definition needed.

**Why direct GitHub API (not git clone)?** Avoids managing git credentials and local state inside the container. The agent reads and writes individual files via the GitHub Contents API.

**Why no confirmation step?** The site is low-risk. The agent makes the change, pushes it, and texts mom a confirmation. If something's wrong, she texts again.

**Why Arize Phoenix?** OTel-native, open source, self-hostable, and specifically good at the "what did the agent actually do" question — not just eval scores.
