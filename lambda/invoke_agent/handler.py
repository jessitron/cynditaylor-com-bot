"""SES → AgentCore dispatcher Lambda.

Triggered by the cyndibot-inbound SES receipt rule (LambdaAction, InvocationType=Event)
*after* the S3Action has written the raw MIME to s3://cyndibot-incoming-emails/emails/.

Filters by recipient username so smoke/test addresses don't spin up agent work,
then calls bedrock-agentcore.invoke_agent_runtime with payload {"s3_key": ...}.

Emits exactly one event per invocation to Honeycomb (dataset configurable via
HONEYCOMB_DATASET, default cyndibot-dispatcher) so we can answer "which emails
got rejected and why" and "how many actually reached the agent" without grepping
CloudWatch.
"""

from __future__ import annotations

import email.utils
import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
import uuid

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-west-2")
RUNTIME_ARN = os.environ["CYNDIBOT_AGENT_RUNTIME_ARN"]
INBOUND_PREFIX = os.environ.get("CYNDIBOT_INBOUND_PREFIX", "emails/")
AGENT_DOMAIN = os.environ.get(
    "CYNDIBOT_AGENT_DOMAIN", "cyndibot.jessitron.honeydemo.io"
)
AGENT_USERNAMES = frozenset(
    u.strip().lower()
    for u in os.environ.get("CYNDIBOT_AGENT_USERNAMES", "cyndi").split(",")
    if u.strip()
)
AGENT_RECIPIENTS = frozenset(f"{u}@{AGENT_DOMAIN}".lower() for u in AGENT_USERNAMES)

HONEYCOMB_API_KEY = os.environ["HONEYCOMB_API_KEY"]
HONEYCOMB_DATASET = os.environ.get("HONEYCOMB_DATASET", "cyndibot-dispatcher")
HONEYCOMB_EVENTS_URL = f"https://api.honeycomb.io/1/events/{HONEYCOMB_DATASET}"

# Hard-coded sender allowlist. Any address @AGENT_DOMAIN is also accepted
# (we control that domain end-to-end via SES + DKIM, so self-loop test
# fixtures like pretend-mom@cyndibot... pass without polluting this list).
ALLOWED_SENDERS = frozenset(
    {
        "jessitron@jessitron.com",
        "jessitron@gmail.com",
        "mamacatitron@gmail.com",
        "taylor777@sbcglobal.net",
    }
)

_agentcore = boto3.client("bedrock-agentcore", region_name=REGION)


def _thread_root_message_id(headers: dict[str, str], own_message_id: str) -> str:
    """Pick the thread-root Message-ID per JWZ-lite.

    1. References: → first Message-ID in the list is the thread root.
    2. Else In-Reply-To: → that Message-ID is the thread root.
    3. Else this email IS the thread root → use its own Message-ID.
    """
    refs = headers.get("references", "").strip()
    if refs:
        first = refs.split()[0]
        return first
    in_reply_to = headers.get("in-reply-to", "").strip()
    if in_reply_to:
        return in_reply_to
    return own_message_id


def _thread_id_from_headers(headers: dict[str, str], own_message_id: str) -> str:
    root = _thread_root_message_id(headers, own_message_id)
    canonical = root.strip().strip("<>").lower()
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"thread-{digest}"


def _matched_agent_recipient(recipients: list[str]) -> str | None:
    for r in recipients:
        if r and r.lower() in AGENT_RECIPIENTS:
            return r.lower()
    return None


def _sender_allowed(addr: str) -> bool:
    a = addr.lower().strip()
    if not a:
        return False
    if a in ALLOWED_SENDERS:
        return True
    _, _, domain = a.partition("@")
    return domain == AGENT_DOMAIN.lower()


def _header_lookup(mail: dict) -> dict[str, str]:
    """Flatten mail.headers (list of {name, value}) into a case-insensitive dict.

    SES Lambda events include the full header list as `mail.headers` by
    default; commonHeaders is a curated subset that omits threading headers
    like In-Reply-To and References, which we need for thread-scoped
    sessions.
    """
    out: dict[str, str] = {}
    for h in mail.get("headers") or []:
        name = (h.get("name") or "").lower()
        if name:
            out[name] = h.get("value") or ""
    return out


def _sender_from_event(mail: dict) -> str:
    # Prefer the From: header so the session id is stable per real sender.
    # mail.source is the SMTP envelope sender, which gets rewritten to a
    # per-message bounce address when SES is the originating MTA (e.g. our
    # smoke loop), so it isn't reliably "mom's email."
    common = mail.get("commonHeaders") or {}
    from_list = common.get("from") or []
    if from_list:
        _, addr = email.utils.parseaddr(from_list[0])
        if addr:
            return addr
    return mail.get("source") or ""


def _send_dispatcher_event(fields: dict) -> None:
    """Best-effort POST to Honeycomb. Logs warnings on failure, never raises.

    Telemetry blips must not retry the Lambda — SES invokes us with
    InvocationType=Event, so a raised exception triggers SES's retry, which
    would mean a duplicate AgentCore invoke for the success case.
    """
    payload = json.dumps(fields, default=str).encode("utf-8")
    req = urllib.request.Request(
        HONEYCOMB_EVENTS_URL,
        data=payload,
        method="POST",
        headers={
            "X-Honeycomb-Team": HONEYCOMB_API_KEY,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                logger.warning(
                    "honeycomb non-200: status=%s body=%s",
                    resp.status,
                    resp.read().decode("utf-8", errors="replace")[:500],
                )
            else:
                logger.info(
                    "honeycomb event sent: invocation.id=%s outcome=%s",
                    fields.get("invocation.id"),
                    fields.get("dispatcher.outcome"),
                )
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500] if hasattr(e, "read") else ""
        logger.warning("honeycomb HTTPError: status=%s body=%s", e.code, body)
    except Exception as e:
        logger.warning("honeycomb send failed: %s: %s", type(e).__name__, e)


def handler(event, context):
    start = time.time()
    fields: dict = {
        "invocation.id": str(uuid.uuid4()),
        "faas.invocation_id": getattr(context, "aws_request_id", "") or "",
        "faas.name": getattr(context, "function_name", "") or "",
        "email.to.agent_addresses": ",".join(sorted(AGENT_RECIPIENTS)),
        "dispatcher.outcome": "unknown",
        "dispatcher.agent_invoked": False,
    }
    logger.info("invocation.id=%s", fields["invocation.id"])

    try:
        records = event.get("Records") or []
        if not records:
            logger.warning("No Records in event; nothing to do")
            fields["dispatcher.outcome"] = "noop_no_records"
            return {"status": "noop", "reason": "no_records"}

        ses = records[0].get("ses") or {}
        mail = ses.get("mail") or {}
        receipt = ses.get("receipt") or {}

        sender = _sender_from_event(mail)
        envelope_sender = mail.get("source") or ""
        message_id = mail.get("messageId") or ""
        recipients = receipt.get("recipients") or []
        sender_domain = sender.partition("@")[2].lower()
        matched_recipient = _matched_agent_recipient(recipients)
        headers = _header_lookup(mail)

        fields.update(
            {
                "email.from": sender,
                "email.envelope_from": envelope_sender,
                "email.from.domain": sender_domain,
                "email.message_id": message_id,
                "email.to": ",".join(recipients),
                "email.to.count": len(recipients),
                "email.to.matched_agent": matched_recipient is not None,
                "email.to.matched_address": matched_recipient or "",
                "email.headers.present": len(headers) > 0,
                "email.headers.count": len(headers),
                "email.headers.names": ",".join(sorted(headers.keys())),
                "email.headers.in_reply_to": headers.get("in-reply-to", ""),
                "email.headers.references": headers.get("references", ""),
                "email.headers.message_id": headers.get("message-id", ""),
            }
        )

        logger.info(
            "ses event: sender=%s envelope_sender=%s message_id=%s recipients=%s",
            sender,
            envelope_sender,
            message_id,
            recipients,
        )

        if matched_recipient is None:
            logger.info(
                "recipient does not match any of %s; skipping (this address is for raw S3 capture only)",
                sorted(AGENT_RECIPIENTS),
            )
            fields["dispatcher.outcome"] = "skipped_recipient_filter"
            return {"status": "skipped", "reason": "recipient_filter", "recipients": recipients}

        if not _sender_allowed(sender):
            logger.warning(
                "sender %s not in allowlist; skipping",
                sender,
            )
            fields["dispatcher.outcome"] = "skipped_sender_not_allowed"
            return {"status": "skipped", "reason": "sender_not_allowed", "sender": sender}

        if not message_id:
            fields["dispatcher.outcome"] = "missing_message_id"
            raise RuntimeError("ses.mail.messageId missing — cannot derive S3 key")

        s3_key = f"{INBOUND_PREFIX}{message_id}"
        own_message_id = headers.get("message-id", "") or f"<{message_id}@ses>"
        thread_id = _thread_id_from_headers(headers, own_message_id)
        invocation_id = fields["invocation.id"]
        payload = json.dumps(
            {
                "s3_key": s3_key,
                "email_thread_id": thread_id,
                "invocation_id": invocation_id,
                "email_from": sender,
            }
        ).encode("utf-8")

        fields.update(
            {
                "session.id": thread_id,
                "email.thread.id": thread_id,
                "aws.s3.key": s3_key,
            }
        )

        logger.info(
            "invoking agent runtime: thread_id=%s invocation_id=%s email_from=%s s3_key=%s",
            thread_id,
            invocation_id,
            sender,
            s3_key,
        )

        try:
            response = _agentcore.invoke_agent_runtime(
                agentRuntimeArn=RUNTIME_ARN,
                runtimeSessionId=thread_id,
                contentType="application/json",
                payload=payload,
            )
        except Exception as exc:
            fields["dispatcher.outcome"] = "agent_invoke_failed"
            fields["dispatcher.error"] = str(exc)[:500]
            fields["dispatcher.error_class"] = type(exc).__name__
            raise

        body = response.get("response")
        body_text = body.read().decode("utf-8") if body is not None else ""
        agent_status = response.get("statusCode")

        fields.update(
            {
                "dispatcher.outcome": "invoked",
                "dispatcher.agent_invoked": True,
                "dispatcher.agent_status_code": int(agent_status) if agent_status is not None else None,
            }
        )

        logger.info(
            "agentcore response: status=%s body=%s",
            agent_status,
            body_text[:1000],
        )

        return {
            "status": "invoked",
            "thread_id": thread_id,
            "invocation_id": invocation_id,
            "s3_key": s3_key,
            "agent_status_code": agent_status,
        }
    except Exception as exc:
        if fields.get("dispatcher.outcome") in (None, "unknown"):
            fields["dispatcher.outcome"] = "error"
        fields.setdefault("dispatcher.error", str(exc)[:500])
        fields.setdefault("dispatcher.error_class", type(exc).__name__)
        raise
    finally:
        fields["dispatcher.duration_ms"] = int((time.time() - start) * 1000)
        _send_dispatcher_event(fields)
