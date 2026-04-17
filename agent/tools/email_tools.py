import email
from email import policy
from email.message import EmailMessage
from typing import Any

import boto3
from strands import tool

INBOUND_BUCKET = "cyndibot-incoming-emails"


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
    }
