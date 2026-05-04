import email
import re
from email import policy
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import Any

import boto3
import pillow_heif
from opentelemetry import trace
from PIL import Image
from strands import tool

from agent.tools.site_tools import WORKSPACE_DIR

pillow_heif.register_heif_opener()

INBOUND_BUCKET = "cyndibot-incoming-emails"
SES_REGION = "us-west-2"
REPLY_FROM = "Cyndibot <bot@cyndibot.jessitron.honeydemo.io>"

# https://aws.amazon.com/ses/pricing/ — marginal rate after free tier.
# Inbound costs (receipt + chunk-charge) are the dispatcher's responsibility;
# see lambda/invoke_agent.
SES_SEND_PRICE_USD = 0.0001

_tracer = trace.get_tracer(__name__)
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")


def _best_body(msg: EmailMessage, content_type: str) -> str:
    part = msg.get_body(preferencelist=(content_type,))
    if part is None:
        return ""
    return part.get_content()


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    cleaned = _FILENAME_SAFE_RE.sub("_", base).lstrip(".")
    if not cleaned:
        cleaned = "attachment"
    return cleaned[:200]


def _is_heic(content_type: str, filename: str) -> bool:
    if content_type.lower() in {"image/heic", "image/heif"}:
        return True
    return filename.lower().endswith((".heic", ".heif"))


def _unique_path(images_dir: Path, name: str) -> Path:
    candidate = images_dir / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    n = 2
    while True:
        candidate = images_dir / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def _convert_heic_to_jpg(payload: bytes, target: Path, original_filename: str) -> int:
    """Convert HEIC bytes to JPG at `target`. Returns final on-disk size.

    Wrapped in its own span so a slow conversion (large iPhone photo)
    surfaces as a discrete operation rather than a stamped attr on the
    parse span. One span per attachment if mom sends multiple HEICs.
    """
    with _tracer.start_as_current_span("convert_heic_to_jpg") as span:
        span.set_attribute("image.original_filename", original_filename)
        span.set_attribute("image.input_bytes", len(payload))
        Image.open(BytesIO(payload)).convert("RGB").save(
            target, format="JPEG", quality=90
        )
        output_bytes = target.stat().st_size
        span.set_attribute("image.output_bytes", output_bytes)
        span.set_attribute(
            "image.target_path", str(target.relative_to(WORKSPACE_DIR))
        )
        return output_bytes


def _write_image_attachment(part, images_dir: Path) -> dict[str, Any]:
    raw_filename = part.get_filename() or "attachment"
    safe_name = _sanitize_filename(raw_filename)
    content_type = part.get_content_type()
    payload = part.get_payload(decode=True)

    if _is_heic(content_type, safe_name):
        target_name = Path(safe_name).stem + ".jpg"
        target = _unique_path(images_dir, target_name)
        final_size = _convert_heic_to_jpg(payload, target, raw_filename)
        final_content_type = "image/jpeg"
    else:
        target = _unique_path(images_dir, safe_name)
        target.write_bytes(payload)
        final_content_type = content_type
        final_size = len(payload)

    return {
        "path": str(target.relative_to(WORKSPACE_DIR)),
        "original_filename": raw_filename,
        "size_bytes": final_size,
        "content_type": final_content_type,
    }


def parse_inbound_impl(s3_key: str) -> dict[str, Any]:
    s3 = boto3.client("s3")
    raw = s3.get_object(Bucket=INBOUND_BUCKET, Key=s3_key)["Body"].read()
    msg: EmailMessage = email.message_from_bytes(raw, policy=policy.default)  # type: ignore[assignment]

    images_dir = WORKSPACE_DIR / "images"
    attachments: list[dict[str, Any]] = []
    bytes_total = 0
    for part in msg.iter_attachments():
        if not part.get_content_type().startswith("image/"):
            continue
        images_dir.mkdir(parents=True, exist_ok=True)
        meta = _write_image_attachment(part, images_dir)
        attachments.append(meta)
        bytes_total += meta["size_bytes"]

    span = trace.get_current_span()
    span.set_attribute("email.attachment.count", len(attachments))
    if attachments:
        span.set_attribute("email.attachment.bytes_total", bytes_total)
        span.set_attribute(
            "email.attachment.types",
            ",".join(a["content_type"] for a in attachments),
        )

    return {
        "from": str(msg.get("From", "")),
        "to": str(msg.get("To", "")),
        "subject": str(msg.get("Subject", "")),
        "date": str(msg.get("Date", "")),
        "body_text": _best_body(msg, "plain"),
        "body_html": _best_body(msg, "html"),
        "message_id": str(msg.get("Message-ID", "")),
        "in_reply_to": str(msg.get("In-Reply-To", "")),
        "references": str(msg.get("References", "")),
        "attachments": attachments,
    }


def send_reply_impl(
    to: str,
    subject: str,
    body_text: str,
    in_reply_to: str = "",
    references: str = "",
) -> dict[str, Any]:
    reply = EmailMessage()
    reply["From"] = REPLY_FROM
    reply["To"] = to
    reply["Subject"] = subject
    if in_reply_to:
        reply["In-Reply-To"] = in_reply_to
        refs = f"{references} {in_reply_to}".strip() if references else in_reply_to
        reply["References"] = refs
    reply.set_content(body_text)

    ses = boto3.client("sesv2", region_name=SES_REGION)
    resp = ses.send_email(
        Content={"Raw": {"Data": reply.as_bytes()}},
    )

    span = trace.get_current_span()
    span.set_attribute("cost.ses.send.qty", 1)
    span.set_attribute("cost.ses.send.price", SES_SEND_PRICE_USD)

    # SES replaces the Message-ID header on raw send. The delivered message's
    # Message-ID is <{MessageId}@us-west-2.amazonses.com>; that's what will
    # appear in any In-Reply-To if the recipient replies.
    return {"ses_message_id": resp["MessageId"]}


@tool
def parse_inbound(s3_key: str) -> dict[str, Any]:
    """Read a raw MIME email from S3 and return its structured fields.

    Args:
        s3_key: Object key inside the cyndibot-incoming-emails bucket
            (e.g. "emails/abc123..."). Usually the value of
            receipt.action.objectKey from the SES notification.

    Returns:
        Dict with from, to, subject, date, body_text, body_html,
        message_id, in_reply_to, references, attachments. Missing
        headers return as empty strings. `date` is the RFC 2822 Date
        header from the email (not the current time) -- use it for
        changelog entries so requests and records line up.

        `attachments` is a list of image attachments that have ALREADY
        been written into the workspace. Each entry has:
          - path: workspace-relative path (e.g. "images/garden.jpg")
          - original_filename: the filename from the email
          - size_bytes: size on disk
          - content_type: final content-type (HEIC is converted to JPG
            so an inbound image/heic shows up here as image/jpeg)
        Empty list when there are no images. The workspace must exist
        before calling this -- run sync_workspace first.
    """
    return parse_inbound_impl(s3_key)


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
        Dict with ses_message_id. Note: SES overrides the Message-ID
        header, so the delivered message's ID is
        <{ses_message_id}@us-west-2.amazonses.com>.
    """
    return send_reply_impl(to, subject, body_text, in_reply_to, references)
