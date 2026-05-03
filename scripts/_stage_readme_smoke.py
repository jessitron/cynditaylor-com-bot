"""Stage an inbound that asks Cyndibot to add a 'cyndibot was here' line to
the README. Drives the first end-to-end agent push to live main.

From = smoketest@cyndibot... so the agent's reply is deliverable in the SES
sandbox AND the changelog entry gets the [TEST] prefix per the agent's
prompt convention. The push to live main happens regardless of the prefix --
that is the whole point of this smoke.
"""

import secrets
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

import boto3

BUCKET = "cyndibot-incoming-emails"
PREFIX = "emails/"
SENDER = "smoketest@cyndibot.jessitron.honeydemo.io"
RECIPIENT = "cyndi@cyndibot.jessitron.honeydemo.io"


def build_message(subject: str, body: str) -> bytes:
    msg = EmailMessage()
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg["Subject"] = subject
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(domain="cyndibot.jessitron.honeydemo.io")
    msg.set_content(body)
    return msg.as_bytes()


def main() -> None:
    subject = "Tiny README update"
    body = (
        "Hi Cyndibot,\n"
        "\n"
        "Could you add a single line to the README saying 'cyndibot was\n"
        "here' followed by today's date in YYYY-MM-DD form? Anywhere\n"
        "near the top is fine. This is a smoke test to confirm you can\n"
        "edit and push a real change.\n"
        "\n"
        "Thanks!\n"
        "Cyndi (smoke test)\n"
    )

    key = f"{PREFIX}readme-smoke-{secrets.token_urlsafe(12)}"
    raw = build_message(subject, body)

    boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=raw)
    print(key)


if __name__ == "__main__":
    main()
