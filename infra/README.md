# Infra log

A running record of every AWS setup step and command for this project. If it changes AWS state, it goes here.

**Account:** jessitron-sandbox (`414852377253`)
**Region:** `us-west-2`

Verify before any AWS work:

```bash
aws sts get-caller-identity
# expect Account = 414852377253
```

## 2026-04-17 — Bedrock access check

No state changes; read-only verification.

```bash
# Confirmed Anthropic models listed in us-west-2
aws bedrock list-foundation-models --region us-west-2 --by-provider anthropic

# Confirmed we can invoke Sonnet 4.5 via its cross-region inference profile
aws bedrock-runtime converse \
  --region us-west-2 \
  --model-id us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Say hello in 5 words."}]}]' \
  --inference-config '{"maxTokens":50}'
```

**Findings:**
- Sonnet 4.5, Haiku 4.5, and Opus 4.5/4.6/4.7 are all ACTIVE in us-west-2.
- Invocation requires an **inference-profile ID** (prefixed `us.` or `global.`), not the bare model ID. Bare IDs return `ValidationException: on-demand throughput isn't supported`.
- Default model for this project: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`.

No IAM roles, no resources, no policies created yet.

## 2026-04-17 — SES inbound email for cyndibot.jessitron.honeydemo.io

Pivot from Twilio SMS (abandoned due to US toll-free A2P compliance) to SES email.

### Findings before changes

- Route 53 zone `jessitron.honeydemo.io.` exists as `/hostedzone/Z0975156EQFWS502JWNW`.
- SES in us-west-2 already had an identity `instruqt.jessitron.honeydemo.io` and an active receipt rule set `instruqt-email-ruleset` with a single rule scoped to that other domain. We add to that same rule set (only one can be active per region).

Scripts in `scripts/` that run these commands (all idempotent where possible):

```bash
scripts/ses-survey                      # list hosted zones, identities, rule sets
scripts/ses-describe-ruleset            # inspect active receipt rule set
scripts/ses-create-identity             # create domain identity, print DKIM tokens
scripts/route53-add-ses-records         # add 3 DKIM CNAMEs + MX for SES inbound
scripts/s3-create-inbound-bucket        # create bucket + SES-write policy
scripts/ses-add-receipt-rule            # add a rule to the existing ruleset
```

### Commands run (state-changing)

```bash
# 1. Create SES domain identity (DKIM-based verification).
aws sesv2 create-email-identity \
  --region us-west-2 \
  --email-identity cyndibot.jessitron.honeydemo.io

# 2. Route 53 CNAMEs (3x DKIM) + MX -> inbound-smtp.us-west-2.amazonaws.com priority 10.
#    Built via scripts/_build_ses_change_batch.py from live DKIM tokens.
aws route53 change-resource-record-sets \
  --hosted-zone-id Z0975156EQFWS502JWNW \
  --change-batch '<generated>'
# ChangeInfo id: /change/C09348254DEPDCSWONNL

# 3. S3 bucket for inbound mail, public access fully blocked.
aws s3api create-bucket \
  --bucket cyndibot-incoming-emails \
  --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
aws s3api put-public-access-block \
  --bucket cyndibot-incoming-emails \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-policy \
  --bucket cyndibot-incoming-emails \
  --policy '<allow ses.amazonaws.com PutObject, SourceAccount=414852377253>'

# 4. Receipt rule added to existing active rule set.
aws ses create-receipt-rule \
  --region us-west-2 \
  --rule-set-name instruqt-email-ruleset \
  --rule '{
    "Name": "cyndibot-inbound",
    "Enabled": true,
    "TlsPolicy": "Optional",
    "Recipients": ["cyndibot.jessitron.honeydemo.io"],
    "Actions": [{"S3Action": {"BucketName": "cyndibot-incoming-emails", "ObjectKeyPrefix": "emails/"}}],
    "ScanEnabled": true
  }'
```

### Current state

- SES identity `cyndibot.jessitron.honeydemo.io`: pending DKIM verification (DNS records just submitted).
- Route 53 change `/change/C09348254DEPDCSWONNL` submitted; propagates in ~60s.
- S3 bucket `cyndibot-incoming-emails` live, private, SES can PutObject.
- Receipt rule `cyndibot-inbound` enabled in active rule set `instruqt-email-ruleset`.
- **SES sandbox still applies to *sending*** — outbound replies can only go to verified addresses until we request production access.

## 2026-04-24 — ECR repo + first image push (AgentCore Phase 2 step 1)

### Scripts

```bash
scripts/container-build       # docker buildx --platform linux/arm64 --load -> cyndibot:local
scripts/container-push-ecr    # ecr login, tag cyndibot:local as <acct>.dkr.ecr...:latest, docker push
```

### Commands run (state-changing)

```bash
# 1. Create ECR repo (scan-on-push, mutable tags so :latest moves).
aws ecr create-repository \
  --repository-name cyndibot \
  --region us-west-2 \
  --image-scanning-configuration scanOnPush=true \
  --image-tag-mutability MUTABLE

# 2. Authenticate + tag + push (via scripts/container-push-ecr).
aws ecr get-login-password --region us-west-2 \
  | docker login --username AWS --password-stdin 414852377253.dkr.ecr.us-west-2.amazonaws.com
docker tag cyndibot:local 414852377253.dkr.ecr.us-west-2.amazonaws.com/cyndibot:latest
docker push 414852377253.dkr.ecr.us-west-2.amazonaws.com/cyndibot:latest
```

### Current state

- ECR repo `cyndibot` (`arn:aws:ecr:us-west-2:414852377253:repository/cyndibot`).
- Image `cyndibot:latest` pushed. Digest `sha256:7a84e51c...dfea70`, 133 MB, OCI image index.
- linux/arm64 only (AgentCore requires arm64).

## 2026-04-24 — IAM role for the AgentCore runtime (Phase 2 step 3)

Policy documents live in `infra/iam/` so they're reviewable:

- `infra/iam/cyndibot-agent-runtime-trust.json` — trust policy.
- `infra/iam/cyndibot-agent-runtime-policy.json` — inline permissions.

### Trust model

- Principal: `bedrock-agentcore.amazonaws.com`.
- Conditions: `aws:SourceAccount = 414852377253` + `aws:SourceArn` LIKE `arn:aws:bedrock-agentcore:us-west-2:414852377253:runtime/*` (confused-deputy prevention).

### Inline permissions (`CyndibotAgentRuntimeInline`)

| Statement | Why |
| --- | --- |
| EcrPullImage | Pull the container image from our ECR repo. |
| CloudWatchLogs (`/aws/bedrock-agentcore/runtimes/*`) | Runtime logs. |
| XRayTracing | Baseline AgentCore requirement. |
| CloudWatchMetrics (ns `bedrock-agentcore`) | Runtime metrics. |
| AgentCoreWorkloadIdentity | `GetWorkloadAccessToken*` — baseline AgentCore. |
| BedrockClaudeInvoke | Invoke/converse on Anthropic foundation models + `us.anthropic.*` inference profiles in our account. |
| InboundMailBucket | `s3:GetObject` on `cyndibot-incoming-emails/*` — read inbound emails. |
| SesSendFromBot | `ses:SendEmail` + `SendRawEmail` on the `cyndibot.jessitron.honeydemo.io` identity. |

### Commands run (state-changing)

```bash
aws iam create-role \
  --role-name CyndibotAgentRuntime \
  --assume-role-policy-document file://infra/iam/cyndibot-agent-runtime-trust.json \
  --description "Execution role for the cyndibot AgentCore runtime"

aws iam put-role-policy \
  --role-name CyndibotAgentRuntime \
  --policy-name CyndibotAgentRuntimeInline \
  --policy-document file://infra/iam/cyndibot-agent-runtime-policy.json
```

### Current state

- Role ARN: `arn:aws:iam::414852377253:role/CyndibotAgentRuntime`.
- No SES production access request yet — sandbox rules still apply. For first cloud invoke this is fine because both sender and recipient are on the verified `cyndibot.jessitron.honeydemo.io` domain.
- No Secrets Manager entry yet for `GITHUB_TOKEN`; we'll add it only when we need `push_site_changes` to work in the cloud.

## 2026-04-30 — AgentCore runtime created and invoked (Phase 2 step 5+6)

### Scripts

```bash
scripts/agentcore-create          # create-agent-runtime with the cyndibot:latest image
scripts/agentcore-wait-ready      # poll until status=READY
scripts/agentcore-smoke-invoke    # stage greeting inbound + invoke runtime
```

### Commands run (state-changing)

```bash
# 1. Create the runtime. Env vars hard-code the OTel exporter at Honeycomb
#    (HONEYCOMB_API_KEY is read from .env at script time and baked into
#    environmentVariables on the runtime — not stored anywhere else by us).
aws bedrock-agentcore-control create-agent-runtime \
  --region us-west-2 \
  --agent-runtime-name cyndibot \
  --agent-runtime-artifact '{"containerConfiguration":{"containerUri":"414852377253.dkr.ecr.us-west-2.amazonaws.com/cyndibot:latest"}}' \
  --role-arn arn:aws:iam::414852377253:role/CyndibotAgentRuntime \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --filesystem-configurations '[{"sessionStorage":{"mountPath":"/mnt/workspace"}}]' \
  --environment-variables <generated by scripts/_build_agentcore_env_json.py>

# 2. First invocation. Used a greeting-style payload that does not exercise
#    git/push, so SES sandbox + missing GITHUB_TOKEN are not constraints.
aws bedrock-agentcore invoke-agent-runtime \
  --region us-west-2 \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-west-2:414852377253:runtime/cyndibot-o2gGSvB6Hz \
  --runtime-session-id smoke-first-cloud-invoke-...-cyndibot-runtime \
  --content-type application/json \
  --payload fileb://<json with s3_key> \
  out.bin
```

### Current state

- Runtime ARN: `arn:aws:bedrock-agentcore:us-west-2:414852377253:runtime/cyndibot-o2gGSvB6Hz`.
- Runtime version: 1, status `READY` (took ~2 min from CREATING to READY).
- First invocation: 200, ~13.7s end-to-end. Reply email landed back in `s3://cyndibot-incoming-emails/emails/`.
- Trace shipped to Honeycomb team `modernity`, env `cynditaylor-com-bot`, dataset `cynditaylor-com-bot`. 12 spans, trace_id `6cb81cf8137235c43ac1c2f6ced9f428`.

### Gotchas captured

- The CLI subcommand for invoke is `aws bedrock-agentcore invoke-agent-runtime` (runtime plane). The CLI for create/get is `aws bedrock-agentcore-control create-agent-runtime` (control plane). Different services.
- `--payload` for `invoke-agent-runtime` is passed as `fileb://path-to-json-file` in the smoke script (not yet tested if inline `--payload '{...}'` works).

## 2026-05-01 — SES → Lambda → AgentCore dispatcher (`lambda/invoke_agent/`)

Self-contained module. Owns its own IAM role (`CyndibotInvokeAgentLambda`) and Lambda function (`cyndibot-invoke-agent`). No ECR — handler is a plain zip with vendored boto3 (Lambda's bundled boto3 may lag the `bedrock-agentcore` client, so we vendor latest to be deterministic).

Mirrors the `collector/` module's layout: `config.env`, `scripts/{bootstrap,build,deploy,wire-into-ses,smoke,delete}`. Each script is idempotent.

Run order on first deploy:

```bash
lambda/invoke_agent/scripts/bootstrap        # IAM role + inline policy
lambda/invoke_agent/scripts/build            # uv pip install boto3 + zip handler.py
lambda/invoke_agent/scripts/deploy           # create-function (or update if exists)
lambda/invoke_agent/scripts/wire-into-ses    # add-permission for ses + update receipt rule
lambda/invoke_agent/scripts/smoke            # full pretend-mom roundtrip via real SES
```

To tear it down (receipt rule reverts to S3-only; raw inbound capture keeps working):

```bash
lambda/invoke_agent/scripts/delete
```

State-changing AWS resources owned by this module:

- IAM role `CyndibotInvokeAgentLambda` + inline policy `CyndibotInvokeAgentInline` (CloudWatch Logs + `bedrock-agentcore:InvokeAgentRuntime` on the cyndibot runtime ARN).
- Lambda function `cyndibot-invoke-agent` (python3.12, arm64, 256MB, 60s timeout). Env vars: `CYNDIBOT_AGENT_RUNTIME_ARN`, `CYNDIBOT_INBOUND_PREFIX`, `CYNDIBOT_AGENT_USERNAME`, `CYNDIBOT_AGENT_DOMAIN`.
- Lambda resource policy statement `ses-invoke-cyndibot-invoke-agent` (`Principal: ses.amazonaws.com`, `AWS:SourceAccount` condition).
- Receipt rule `cyndibot-inbound` in `instruqt-email-ruleset` updated to `Actions = [S3Action, LambdaAction]`. Lambda action is `InvocationType=Event` so SES doesn't wait for the agent's ~30s run.

### Design notes worth keeping

- **`runtimeSessionId` keying:** `mom-<sha256(from_header_addr)>`. We use the From: header (`mail.commonHeaders.from[0]`), not the SMTP envelope sender (`mail.source`), because SES rewrites the envelope-from to a per-message bounce mailbox when SES itself is the originating MTA (i.e. our self-loop tests). For real moms emailing from gmail both fields would resolve to her address; using From also makes the session stable for the smoke loop. Use `lambda/invoke_agent/scripts/_print_session_id.py <addr>` to compute the expected ID.
- **Recipient filter:** Lambda only invokes the agent for `cyndi@cyndibot.jessitron.honeydemo.io` (configurable via `CYNDIBOT_AGENT_USERNAME`). Other addresses on the domain — `pretend-mom@`, `smoketest-*@`, agent-reply round-trips — still land in S3 via the S3Action but the Lambda no-ops on them. This is what lets the agent send replies to `pretend-mom@cyndibot…` for self-loop testing without infinite recursion.
- **Vendored boto3:** ~15 MB zip. If/when Lambda's bundled boto3 catches up to bedrock-agentcore, we can drop the vendored copy and use a pure handler.

## OTel collector Lambda — see `collector/`

Self-contained module. Owns its own ECR repo, IAM role, Lambda, and Function URL. State-changing commands (ECR repo, IAM role, Lambda CRUD) are driven by scripts in `collector/scripts/`. Run order on first deploy:

```bash
collector/scripts/bootstrap         # creates ECR repo cyndibot-collector + IAM role CyndibotCollectorLambda
collector/scripts/build
collector/scripts/push-ecr
collector/scripts/deploy            # creates lambda cyndibot-collector + function URL (auth=NONE)
```

Function URL auth is `NONE` because the collector enforces a bearer token internally; the OTel Python SDK doesn't sign with Sigv4, so IAM auth would mean writing a custom signing exporter. Bearer token lives in `collector/.env` (gitignored), generated at `bootstrap` time.

When state actually gets created, append a dated section here with the same shape as the AgentCore entries above.
