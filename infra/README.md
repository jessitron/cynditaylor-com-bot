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
