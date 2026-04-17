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
