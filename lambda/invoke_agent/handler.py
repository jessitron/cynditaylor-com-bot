"""SES → AgentCore dispatcher Lambda.

Triggered by the cyndibot-inbound SES receipt rule (LambdaAction, InvocationType=Event)
*after* the S3Action has written the raw MIME to s3://cyndibot-incoming-emails/emails/.

Filters by recipient username so smoke/test addresses don't spin up agent work,
then calls bedrock-agentcore.invoke_agent_runtime with payload {"s3_key": ...}.
"""

from __future__ import annotations

import email.utils
import hashlib
import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-west-2")
RUNTIME_ARN = os.environ["CYNDIBOT_AGENT_RUNTIME_ARN"]
INBOUND_PREFIX = os.environ.get("CYNDIBOT_INBOUND_PREFIX", "emails/")
AGENT_USERNAME = os.environ.get("CYNDIBOT_AGENT_USERNAME", "cyndi")
AGENT_DOMAIN = os.environ.get(
    "CYNDIBOT_AGENT_DOMAIN", "cyndibot.jessitron.honeydemo.io"
)
AGENT_RECIPIENT = f"{AGENT_USERNAME}@{AGENT_DOMAIN}".lower()

_agentcore = boto3.client("bedrock-agentcore", region_name=REGION)


def _runtime_session_id(sender: str) -> str:
    digest = hashlib.sha256(sender.lower().encode("utf-8")).hexdigest()
    return f"mom-{digest}"


def _agent_recipient_match(recipients: list[str]) -> bool:
    for r in recipients:
        if r and r.lower() == AGENT_RECIPIENT:
            return True
    return False


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


def handler(event, context):
    records = event.get("Records") or []
    if not records:
        logger.warning("No Records in event; nothing to do")
        return {"status": "noop", "reason": "no_records"}

    ses = records[0].get("ses") or {}
    mail = ses.get("mail") or {}
    receipt = ses.get("receipt") or {}

    sender = _sender_from_event(mail)
    envelope_sender = mail.get("source") or ""
    message_id = mail.get("messageId") or ""
    recipients = receipt.get("recipients") or []

    logger.info(
        "ses event: sender=%s envelope_sender=%s message_id=%s recipients=%s",
        sender,
        envelope_sender,
        message_id,
        recipients,
    )

    if not _agent_recipient_match(recipients):
        logger.info(
            "recipient does not match %s; skipping (this address is for raw S3 capture only)",
            AGENT_RECIPIENT,
        )
        return {"status": "skipped", "reason": "recipient_filter", "recipients": recipients}

    if not message_id:
        raise RuntimeError("ses.mail.messageId missing — cannot derive S3 key")

    s3_key = f"{INBOUND_PREFIX}{message_id}"
    session_id = _runtime_session_id(sender)
    payload = json.dumps({"s3_key": s3_key}).encode("utf-8")

    logger.info(
        "invoking agent runtime: session_id=%s s3_key=%s",
        session_id,
        s3_key,
    )

    response = _agentcore.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=session_id,
        contentType="application/json",
        payload=payload,
    )

    body = response.get("response")
    body_text = body.read().decode("utf-8") if body is not None else ""
    logger.info(
        "agentcore response: status=%s body=%s",
        response.get("statusCode"),
        body_text[:1000],
    )

    return {
        "status": "invoked",
        "session_id": session_id,
        "s3_key": s3_key,
        "agent_status_code": response.get("statusCode"),
    }
