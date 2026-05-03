"""Send a realistic inbound email via SES FROM a pretend-mom address.

Uses the verified cyndibot.jessitron.honeydemo.io domain for both ends.
SES routes the message through its outbound pipeline, delivers it to our
own inbound-smtp endpoint (via the MX we set up), and the receipt rule
drops the raw MIME into S3 -- same path real mom's mail would follow.

Prints nothing on the happy path except the SES MessageId.
"""

from email.message import EmailMessage

import boto3

FROM_ADDR = "Pretend Mom <pretend-mom@cyndibot.jessitron.honeydemo.io>"
TO_ADDR = "pretend-bot@cyndibot.jessitron.honeydemo.io"
SUBJECT = "Add a line to the test page"
BODY = (
    "Hi Cyndibot,\n"
    "\n"
    "Please append a one-line dated entry to tests.html (create it\n"
    "if it doesn't exist yet -- it's just a scratch page for dev-loop\n"
    "smokes, not linked from the nav). The entry should say\n"
    "\"pretend-mom-roundtrip ran\" with today's date.\n"
    "\n"
    "Thanks!\n"
    "Cyndi (pretending)\n"
)


def main() -> None:
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = TO_ADDR
    msg["Subject"] = SUBJECT
    msg.set_content(BODY)

    ses = boto3.client("sesv2", region_name="us-west-2")
    resp = ses.send_email(Content={"Raw": {"Data": msg.as_bytes()}})
    print(resp["MessageId"])


if __name__ == "__main__":
    main()
