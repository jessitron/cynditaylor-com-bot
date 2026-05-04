# Slice: Thread-scoped session id

Status: planned, not started.

## Goal

Repoint AgentCore's `runtimeSessionId` (and the OTel `session.id` resource attribute) at the **email thread**, not the sender. Add `email.from`, `email.thread.id`, and `invocation.id` as first-class queryable dimensions across the dispatcher event, CloudWatch logs, and the agent's root span.

## Why

The current scheme (`session.id = mom-<sha256(from)>`) was chosen on 2026-05-03 because AgentCore guarantees one microVM per session — so we picked something stable per real-life mom to keep the microVM warm across her emails. Two problems showed up under closer reading:

1. **Strands `Agent` conversation history leaks across unrelated emails.** `agent/server.py:10-18` caches the `Agent` instance globally for the microVM's lifetime. With per-sender session ids, mom's second email starts with the full message history of her first — including the prior reply, tool calls, etc. That's a real footgun: the agent might say "I already added that" when it shouldn't, or hit context limits over time.
2. **Semantic confusion.** `session.id = "this human"` is weird. Standard meaning of "session" is "this conversation."

Per-thread fixes both:

- New thread → new microVM → fresh `_agent` → no contamination between unrelated requests.
- Reply in same thread → same warm microVM → same `_agent` with prior context → "make the photo bigger" actually knows which photo.

## Target behavior

| Scenario | What happens |
|---|---|
| Mom sends a fresh email | New thread id → new microVM → fresh agent → clean conversation. |
| Mom replies in the same thread | Same thread id → same warm microVM → same agent, retains prior context. |
| Mom sends two unrelated requests in parallel | Two thread ids → two microVMs → no contamination, no serialization. |
| Forward-and-reply within a thread | Still the same thread id, gets routed to the same warm agent with prior context. |

The `_get_agent` cache stays as-is — one microVM = one thread, so cache-for-microVM-lifetime = cache-for-thread-lifetime, which is exactly right.

## The three IDs

| Field | Value | Purpose |
|---|---|---|
| `email.from` | sender's address from `From:` header (already present as `email.from`) | "all emails from this person" |
| `email.thread.id` | `thread-<sha256(thread-root-message-id)>` | "all emails in this conversation" |
| `invocation.id` | uuid4 per Lambda invocation (today's `event_id`, renamed) | "this specific email" |
| `session.id` | same value as `email.thread.id` | OTel-conventional dimension; redundant but communicates well in queries |

`email.thread.id` and `session.id` carrying the same value is deliberate — keeps the OTel-conventional name in place for cross-tool queries, while making the domain meaning explicit.

## Thread id derivation (JWZ-lite)

In priority order, against the email's headers:

1. If `References:` is present → first `Message-ID` in the list is the thread root.
2. Else if `In-Reply-To:` is present → that `Message-ID` is the thread root.
3. Else → this email IS the thread root; use its own `Message-ID`.

Then: strip angle brackets, lowercase, sha256 → `thread-<digest>`.

This is not a fallback chain in the sense the project guidelines warn against — each branch is the *correct* answer for the kind of email it describes. A message with no In-Reply-To/References genuinely is the start of a thread.

## Verification gate before coding

The dispatcher needs `In-Reply-To` and `References` headers, which are NOT in `mail.commonHeaders`. AWS docs say SES Lambda events include `mail.headers` (the full header list) by default, but I want to confirm against a real event before betting on it. Two paths if confirmed false:

- (a) Configure the receipt rule to include all headers (if there's a knob).
- (b) Have the dispatcher fetch the raw MIME from S3 and parse headers there. Adds one S3 read of latency to the dispatcher; acceptable.

**First task when work begins:** print `mail.headers` from a real SES Lambda invocation. Maybe extend `scripts/_peek_inbound_headers.py`, or write a one-shot in the Lambda log path.

## Implementation tasks

1. **Verify `mail.headers` is on the SES Lambda event.** If yes, proceed. If no, decide between rule-config knob and S3 re-read; document the decision here before continuing.
2. **`lambda/invoke_agent/handler.py`:**
   - Add `_thread_id_from_headers(mail) -> str` implementing JWZ-lite above.
   - Rename `event_id` → `invocation.id` in the Honeycomb event field. (Internal var name can stay; the *exported attribute* is what matters.)
   - Compute `thread_id = _thread_id_from_headers(mail)` and use it as both the Honeycomb event's `email.thread.id` and `session.id`, AND as `runtimeSessionId` in the `invoke_agent_runtime` call.
   - Expand the agent payload from `{"s3_key": ...}` to `{"s3_key": ..., "email_thread_id": ..., "invocation_id": ..., "email_from": ...}`.
   - Add the three IDs to the `logger.info("invoking agent runtime: ...")` line.
3. **`agent/server.py::invoke`:**
   - Read `email_thread_id`, `invocation_id`, `email_from` from payload.
   - Stamp them as span attributes on the `agent.invocation` root span (`session.id` is already inherited from Resource — leave that alone).
   - Verify the `_get_agent(context.session_id)` cache continues to work: it should, because microVM = one session = one thread now.
4. **`agent/inbound.py` (local non-AgentCore path):**
   - Decide whether to add parity. Likely yes — generate a local `invocation_id` and let `email_thread_id` be empty when running directly. Otherwise local traces silently drop these dimensions.
5. **`agent/observability.py` and `agent/tools/email_tools.py`:**
   - `get_session_id()` keeps working unchanged. The `session: <id>` reply footer now says the thread id.
   - Decide if the footer label should change from `session:` to `thread:` for clarity. Mom doesn't read it; we read it. Probably worth changing.
6. **Smoke verification:**
   - `lambda/invoke_agent/scripts/smoke` (and `smoke-deny`) — confirm new fields land in the dispatcher's Honeycomb event.
   - `scripts/agentcore-smoke-invoke` — confirm new fields land on the agent's `agent.invocation` span.
   - End-to-end: send mom email A and mom email B as separate threads. Verify two distinct `session.id` / `email.thread.id` values. Then send a reply to A. Verify same `session.id` as A, but new `invocation.id`.
   - End-to-end: confirm conversation-history continuity within a thread (e.g., agent asks for clarification in email A's reply, mom replies, agent's reply references prior context). The trace should show prior tool calls in the second invocation's input messages.
7. **`notes/TELEMETRY.md`:** update the "session.id on every agent span" section to reflect the new semantic. The Resource-attr-not-SpanProcessor decision still holds; only the *value* changes.
8. **`notes/ACTIVE.md`:** update the "Decisions locked in so far" line about session model to reflect the new scheme. Add an end-of-session retro when this slice ships.

## Risks / things to flag

- **Cold start per new thread.** Negligible for mom's volume (a few emails a day at most). Worth noting if usage shape ever changes.
- **`_check_session_in_reply.py`** still works as-is (it just sets `obs._SESSION_ID` to a string and checks the footer); no change needed unless we rename the footer label.
- **The dispatcher's CloudWatch retention.** If we expect to query CloudWatch by thread id, make sure log lines actually include it (task 2 above). Honeycomb is the primary query target, but `aws logs tail` is what we reach for first when something looks broken.
- **`email.thread.id` and `session.id` having identical values** is intentional. Confirmed acceptable: the redundancy buys cross-tool query clarity (OTel conventions for one, domain-natural name for the other).

## Open questions to resolve when work begins

- Reply footer wording (`session:` vs `thread:`).
- `agent/inbound.py` parity: stamp invocation_id locally, or skip?
- Whether to also fold `email.from` into the agent's Resource (so it's a column on every span) or keep it as a span-attribute on `agent.invocation` only. Resource means "every span has it but every microVM bakes it in for life" — fine when microVM = thread = one sender, but feels like overreach. Span attr is more honest.
