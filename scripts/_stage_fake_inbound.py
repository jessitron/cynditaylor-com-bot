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
    subject = "Please update my website"
    body = (
        "Hi Cyndi,\n"
        "\n"
        "Please change the headline on the home page from \"Welcome\" to "
        "\"Welcome, friends!\" when you get a chance.\n"
        "\n"
        "Thanks!\n"
    )

    key = f"{PREFIX}fake-{secrets.token_urlsafe(16)}"
    raw = build_message(subject, body)

    boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=raw)
    print(key)


if __name__ == "__main__":
    main()
