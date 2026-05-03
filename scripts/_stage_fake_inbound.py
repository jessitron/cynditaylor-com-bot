"""Write a synthetic inbound email to the SES S3 bucket so the agent has
something realistic to parse during dev loops.

From = smoketest@cyndibot.jessitron.honeydemo.io so that when the agent
replies, SES sandbox still accepts it. Prints the staged s3 key on stdout
so a wrapping shell script can feed it to the agent.
"""

import secrets
import sys
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from datetime import datetime, timezone

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
    subject = "Add a line to the test page"
    body = (
        "Hi Cyndibot,\n"
        "\n"
        "Please append a one-line dated entry to tests.html (create it\n"
        "if it doesn't exist yet -- it's just a scratch page for dev-loop\n"
        "smokes, not linked from the nav). The entry should say\n"
        "\"agent-fake-roundtrip ran\" with today's date.\n"
        "\n"
        "Thanks!\n"
        "Cyndi (smoketest fake-roundtrip)\n"
    )

    key = f"{PREFIX}fake-{secrets.token_urlsafe(16)}"
    raw = build_message(subject, body)

    boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=raw)
    print(key)


if __name__ == "__main__":
    main()
