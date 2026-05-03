# 2026-05-03 — SES IAM fix from a Honeycomb trace

Trace: `d732e523c736750ab48b83c7a4117004` (env `cynditaylor-com-bot`).

## The bug

First real cloud roundtrip failed: AgentCore runtime tried to SES-send a reply to `jessitron@gmail.com` and got `AccessDeniedException` on `ses:SendRawEmail`. Span attribute `exception.message` named the *recipient* identity as the unauthorized resource:

```
not authorized to perform `ses:SendRawEmail' on resource
arn:aws:ses:us-west-2:414852377253:identity/jessitron@gmail.com
```

Cause: the inline policy's `SesSendFromBot` statement only listed `identity/cyndibot.jessitron.honeydemo.io`. SES (in sandbox mode) IAM-checks both From and recipient identities; the recipient check failed before SES's own sandbox check ran.

## Fix

Broadened `SesSendFromBot.Resource` to `arn:aws:ses:us-west-2:414852377253:identity/*` in `infra/iam/cyndibot-agent-runtime-policy.json`, reapplied with `aws iam put-role-policy`. Verified with `aws iam simulate-principal-policy` that both the bot domain identity and `jessitron@gmail.com` now allow `SendRawEmail` and `SendEmail`. Recorded in `infra/README.md` (dated section + summary table row).

Sandbox-mode delivery still requires each recipient to be a verified SES identity; this just stops IAM from blocking before SES gets a chance.

## Strands records exceptions as attributes, not events

The tool span had `event_count: 0` but the exception detail was on the span itself as `exception.message` / `exception.type` / `exception.stacktrace`. So when looking at a failed `execute_tool` span in this codebase, query those columns directly — don't go hunting for span events.

## Honeycomb MCP gotchas hit (worth knowing)

1. **`find_columns` doesn't recall OTel-standard prefixes well.** Searching for `"exception"` returned 50 fuzzy matches like `message`, `type`, `event_id` — but not `exception.message`/`exception.type`/`exception.stacktrace`. Filed feedback via the MCP `feedback` tool.

2. **The local `validate-query.sh` PreToolUse hook has a stale schema cache.** It blocked queries on `exception.*` claiming "columns not found in cached schema" even though the columns exist. Workaround that worked: `get_dataset_columns(environment_slug, dataset_slug, columns=["exception.message", ...])` returns the full schema (295 columns) and refreshes the cache enough that the validator stops blocking. So when a query gets rejected on a "not in cached schema" error for a column you're sure exists, run `get_dataset_columns` first.

3. **`get_trace` with `show_events: true` doesn't render event payloads.** It only adds an `event_count` column. To see actual span events in this dataset model, query the dataset filtering on `trace.parent_id = <span_id>` and `meta.annotation_type = span_event`. (Didn't matter for this trace — the exception was attribute-only — but worth knowing.)
