# Slice: Thread-scoped session id

Status: shipped 2026-05-04.

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

| Scenario                                     | What happens                                                                     |
| -------------------------------------------- | -------------------------------------------------------------------------------- |
| Mom sends a fresh email                      | New thread id → new microVM → fresh agent → clean conversation.                  |
| Mom replies in the same thread               | Same thread id → same warm microVM → same agent, retains prior context.          |
| Mom sends two unrelated requests in parallel | Two thread ids → two microVMs → no contamination, no serialization.              |
| Forward-and-reply within a thread            | Still the same thread id, gets routed to the same warm agent with prior context. |

The `_get_agent` cache stays as-is — one microVM = one thread, so cache-for-microVM-lifetime = cache-for-thread-lifetime, which is exactly right.

## The three IDs

| Field             | Value                                                                  | Purpose                                                                 |
| ----------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `email.from`      | sender's address from `From:` header (already present as `email.from`) | "all emails from this person"                                           |
| `email.thread.id` | `thread-<sha256(thread-root-message-id)>`                              | "all emails in this conversation"                                       |
| `invocation.id`   | uuid4 per Lambda invocation (today's `event_id`, renamed)              | "this specific email"                                                   |
| `session.id`      | same value as `email.thread.id`                                        | OTel-conventional dimension; redundant but communicates well in queries |

`email.thread.id` and `session.id` carrying the same value is deliberate — keeps the OTel-conventional name in place for cross-tool queries, while making the domain meaning explicit.

## Thread id derivation (JWZ-lite)

In priority order, against the email's headers:

1. If `References:` is present → first `Message-ID` in the list is the thread root.
2. Else if `In-Reply-To:` is present → that `Message-ID` is the thread root.
3. Else → this email IS the thread root; use its own `Message-ID`.

Then: strip angle brackets, lowercase, sha256 → `thread-<digest>`.

This is not a fallback chain in the sense the project guidelines warn against — each branch is the _correct_ answer for the kind of email it describes. A message with no In-Reply-To/References genuinely is the start of a thread.

## Verification gate before coding

The dispatcher needs `In-Reply-To` and `References` headers, which are NOT in `mail.commonHeaders`. AWS docs say SES Lambda events include `mail.headers` (the full header list) by default, but I want to confirm against a real event before betting on it.

**Status: verified 2026-05-04.** Approach: stamped the dispatcher's Honeycomb event with `email.headers.{names,count,in_reply_to,references,message_id}`, then ran `lambda/invoke_agent/scripts/smoke-reply` (a new reply-style smoke that sets In-Reply-To + References on the outgoing pretend-mom email). The dispatcher event came back with both fields populated and `email.headers.names` listing `in-reply-to,references` alongside the rest. SES preserves the threading headers as expected — no S3 re-read or receipt-rule knob needed. The header attributes stay on the dispatcher event going forward; cheap and good for debugging.

## Implementation tasks

1. **Verify `mail.headers` is on the SES Lambda event.** If yes, proceed. If no, decide between rule-config knob and S3 re-read; document the decision here before continuing.
2. **`lambda/invoke_agent/handler.py`:**
   - Add `_thread_id_from_headers(mail) -> str` implementing JWZ-lite above.
   - Rename `event_id` → `invocation.id` in the Honeycomb event field. (Internal var name can stay; the _exported attribute_ is what matters.)
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
7. **`notes/TELEMETRY.md`:** update the "session.id on every agent span" section to reflect the new semantic. The Resource-attr-not-SpanProcessor decision still holds; only the _value_ changes.
8. **`notes/ACTIVE.md`:** update the "Decisions locked in so far" line about session model to reflect the new scheme. Add an end-of-session retro when this slice ships.

## Risks / things to flag

- **Cold start per new thread.** Negligible for mom's volume (a few emails a day at most). Worth noting if usage shape ever changes.
- **The dispatcher's CloudWatch retention.** If we expect to query CloudWatch by thread id, make sure log lines actually include it (task 2 above). Honeycomb is the primary query target.
- **`email.thread.id` and `session.id` having identical values** is intentional. It expresses that we're scoping session to email thread.

## Open questions resolved

- `agent/inbound.py` parity: **yes** — local CLI generates a uuid4 `invocation.id` and stamps it on the `agent.invocation` span. `email_thread_id` stays empty when running directly (no inbound thread context).
- Fold `email.from` into the agent's Resource: **yes**, done. `email.from` and `email.thread.id` both ride on the Resource alongside `session.id`. Constant for the whole microVM lifetime, which is one thread.

## Retro

- **Verification gate paid off.** Stamping `email.headers.{names,in_reply_to,references,...}` onto the existing dispatcher Honeycomb event was a low-cost way to confirm SES populates `mail.headers` with In-Reply-To/References. Beat any temporary log-line approach: queryable, kept around for free, no second deploy. The header attrs stay on the dispatcher event going forward.
- **`smoke-reply` is worth keeping.** Sends a pretend-mom email with In-Reply-To + References preset. Mirrors `smoke` but exercises the threaded-reply path. Useful regression check any time threading logic changes.
- **`session.id` and `email.thread.id` carry the same value.** Intentional. `session.id` is OTel-conventional and what cross-tool queries default to; `email.thread.id` makes the domain meaning explicit. Cheap to carry both columns.
- **What I'd do differently:** the implementation was small and fell out cleanly — Resource carries thread/from, `agent.invocation` span carries invocation.id. Nothing to second-guess. The only friction was renaming `event_id` → `invocation.id` across the dispatcher's log line, the verifier script's regex, and the smoke scripts; a single rename ripples through more than expected because the Honeycomb log-format is grep'd by tooling.
