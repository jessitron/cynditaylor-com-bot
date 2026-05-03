"""Stage a synthetic inbound email carrying two image attachments
(one HEIC, one JPEG) to the SES S3 bucket. Tiny generated images, not
real photos. Prints the staged s3 key on stdout.

Used by scripts/smoke-parse-attachments to exercise parse_inbound's
attachment-extraction + HEIC-conversion path without running the LLM
loop or pushing to the live site."""

import secrets
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from io import BytesIO

import boto3
import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

BUCKET = "cyndibot-incoming-emails"
PREFIX = "emails/"
SENDER = "smoketest-pictures@cyndibot.jessitron.honeydemo.io"
RECIPIENT = "cyndi@cyndibot.jessitron.honeydemo.io"


def make_jpeg_bytes(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def make_heic_bytes(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = BytesIO()
    img.save(buf, format="HEIF")
    return buf.getvalue()


def build_message() -> bytes:
    msg = EmailMessage()
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg["Subject"] = "smoke: picture attachments"
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(domain="cyndibot.jessitron.honeydemo.io")
    msg.set_content(
        "Hi Cyndibot,\n"
        "\n"
        "Two test photos attached -- one HEIC, one JPEG. This is a parse\n"
        "smoke test; no site change expected.\n"
        "\n"
        "-- smoketest-pictures\n"
    )

    msg.add_attachment(
        make_heic_bytes((220, 80, 80)),
        maintype="image",
        subtype="heic",
        filename="smoke-red.heic",
    )
    msg.add_attachment(
        make_jpeg_bytes((80, 160, 220)),
        maintype="image",
        subtype="jpeg",
        filename="smoke-blue.jpg",
    )

    return msg.as_bytes()


def main() -> None:
    key = f"{PREFIX}smoke-pictures-{secrets.token_urlsafe(12)}"
    boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=build_message())
    print(key)


if __name__ == "__main__":
    main()
