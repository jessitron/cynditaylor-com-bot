"""Send a synthetic pretend-mom email TO <AGENT_USERNAME>@<domain> via SES.

The dispatcher Lambda accepts a set of aliases (CYNDIBOT_AGENT_USERNAMES,
e.g. cyndi,bot,robot,jeeves). The caller (smoke) selects which alias to
exercise and exports it as AGENT_USERNAME before running this script. A
simple greeting is used so we don't burn site-edit work on a smoke test —
the agent will parse, see no edit is requested, and send a short reply.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from email.message import EmailMessage

import boto3

DOMAIN = os.environ.get("AGENT_DOMAIN", "cyndibot.jessitron.honeydemo.io")
USERNAME = os.environ.get("AGENT_USERNAME", "cyndi")
REGION = os.environ.get("AWS_REGION", "us-west-2")


def main() -> None:
    from_addr = f"Pretend Mom <pretend-mom@{DOMAIN}>"
    to_addr = f"{USERNAME}@{DOMAIN}"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = f"Lambda dispatcher smoke {stamp}"
    msg.set_content(
        "Hi Cyndibot,\n"
        "\n"
        "Just saying hi from the lambda dispatcher smoke test. No edits needed.\n"
        "\n"
        "Thanks,\n"
        "Pretend Mom\n"
    )

    ses = boto3.client("sesv2", region_name=REGION)
    resp = ses.send_email(Content={"Raw": {"Data": msg.as_bytes()}})
    sys.stdout.write(resp["MessageId"])


if __name__ == "__main__":
    main()
