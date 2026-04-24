"""Stage a synthetic greeting-style inbound for container smoke tests.

No concrete edit intent, so the agent should reply with a clarifying
question and NOT exercise the git tools. Prints the staged s3 key on
stdout so a wrapping shell script can feed it to /invocations.
"""

import secrets
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

import boto3

BUCKET = "cyndibot-incoming-emails"
PREFIX = "emails/"
SENDER = "smoketest-container@cyndibot.jessitron.honeydemo.io"
RECIPIENT = "cyndi@cyndibot.jessitron.honeydemo.io"


def build_message() -> bytes:
    msg = EmailMessage()
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg["Subject"] = "just checking in"
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(domain="cyndibot.jessitron.honeydemo.io")
    msg.set_content(
        "Hi Cyndibot, are you there? Just saying hello.\n"
        "\n"
        "(no change needed)\n"
    )
    return msg.as_bytes()


def main() -> None:
    key = f"{PREFIX}smoke-container-{secrets.token_urlsafe(12)}"
    boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=build_message())
    print(key)


if __name__ == "__main__":
    main()
