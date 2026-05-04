"""Send a fake reply (In-Reply-To + References set) to verify SES preserves
threading headers in `mail.headers` on the Lambda event.

Usage:
    AGENT_DOMAIN=... AGENT_USERNAME=cyndi AWS_REGION=us-west-2 \\
        python scripts/_send_reply_smoke_email.py [parent-message-id]

If parent-message-id is omitted, a synthetic one is generated. The actual
parent doesn't have to exist — we just need In-Reply-To/References on the
wire so we can confirm SES surfaces them on the dispatcher's Lambda event.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage

import boto3

DOMAIN = os.environ.get("AGENT_DOMAIN", "cyndibot.jessitron.honeydemo.io")
USERNAME = os.environ.get("AGENT_USERNAME", "cyndi")
REGION = os.environ.get("AWS_REGION", "us-west-2")


def main() -> None:
    parent_mid = sys.argv[1] if len(sys.argv) > 1 else f"<synthetic-{uuid.uuid4().hex}@{DOMAIN}>"
    if not parent_mid.startswith("<"):
        parent_mid = f"<{parent_mid}>"

    from_addr = f"Pretend Mom <pretend-mom@{DOMAIN}>"
    to_addr = f"{USERNAME}@{DOMAIN}"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = f"Re: thread-header smoke {stamp}"
    msg["In-Reply-To"] = parent_mid
    msg["References"] = parent_mid
    msg.set_content(
        "Hi Cyndibot,\n"
        "\n"
        "Reply with In-Reply-To/References set to verify SES preserves them.\n"
        "\n"
        "Thanks,\n"
        "Pretend Mom\n"
    )

    ses = boto3.client("sesv2", region_name=REGION)
    resp = ses.send_email(Content={"Raw": {"Data": msg.as_bytes()}})
    sys.stdout.write(resp["MessageId"])


if __name__ == "__main__":
    main()
