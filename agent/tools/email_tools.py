import email
from email import policy
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any

import boto3
from strands import tool

INBOUND_BUCKET = "cyndibot-incoming-emails"
SES_REGION = "us-west-2"
REPLY_FROM = "Cyndibot <bot@cyndibot.jessitron.honeydemo.io>"


def _best_body(msg: EmailMessage, content_type: str) -> str:
    part = msg.get_body(preferencelist=(content_type,))
    if part is None:
        return ""
    return part.get_content()


@tool
def parse_inbound(s3_key: str) -> dict[str, Any]:
    """Read a raw MIME email from S3 and return its structured fields.

    Args:
        s3_key: Object key inside the cyndibot-incoming-emails bucket
            (e.g. "emails/abc123..."). Usually the value of
            receipt.action.objectKey from the SES notification.

    Returns:
        Dict with from, to, subject, body_text, body_html, message_id,
        in_reply_to. Missing headers return as empty strings.
    """
    s3 = boto3.client("s3")
    raw = s3.get_object(Bucket=INBOUND_BUCKET, Key=s3_key)["Body"].read()
    msg: EmailMessage = email.message_from_bytes(raw, policy=policy.default)  # type: ignore[assignment]

    return {
        "from": str(msg.get("From", "")),
        "to": str(msg.get("To", "")),
        "subject": str(msg.get("Subject", "")),
        "body_text": _best_body(msg, "plain"),
        "body_html": _best_body(msg, "html"),
        "message_id": str(msg.get("Message-ID", "")),
        "in_reply_to": str(msg.get("In-Reply-To", "")),
        "references": str(msg.get("References", "")),
    }


@tool
def send_reply(
    to: str,
    subject: str,
    body_text: str,
    in_reply_to: str = "",
    references: str = "",
) -> dict[str, Any]:
    """Send a plain-text email reply via SES.

    Args:
        to: Recipient address (the original sender you want to reply to).
        subject: Reply subject. Caller should prefix "Re: " if appropriate.
        body_text: Plain text body of the reply.
        in_reply_to: Original Message-ID (including angle brackets). Sets
            the In-Reply-To header so mail clients thread the reply.
        references: Original References header, or empty. The new
            message's References will be `references + " " + in_reply_to`.

    Returns:
        Dict with message_id (SES) and our outgoing Message-ID header.
    """
    reply = EmailMessage()
    reply["From"] = REPLY_FROM
    reply["To"] = to
    reply["Subject"] = subject
    reply["Message-ID"] = make_msgid(domain="cyndibot.jessitron.honeydemo.io")
    if in_reply_to:
        reply["In-Reply-To"] = in_reply_to
        refs = f"{references} {in_reply_to}".strip() if references else in_reply_to
        reply["References"] = refs
    reply.set_content(body_text)

    ses = boto3.client("sesv2", region_name=SES_REGION)
    resp = ses.send_email(
        Content={"Raw": {"Data": reply.as_bytes()}},
    )
    return {
        "ses_message_id": resp["MessageId"],
        "outgoing_message_id": str(reply.get("Message-ID", "")),
    }
