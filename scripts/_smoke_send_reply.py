"""Direct smoke test of agent.tools.email_tools.send_reply.

Sends an email from bot@cyndibot.jessitron.honeydemo.io to
smoketest@cyndibot.jessitron.honeydemo.io. Both sides are at a verified
SES domain (so sandbox accepts it), and the cyndibot-inbound receipt
rule will capture the incoming copy in s3://cyndibot-incoming-emails/
where `scripts/ses-show-inbound` can display it.

Not routed through the agent yet — just verifies the SES send path and
that our threading headers round-trip correctly.
"""

from agent.tools.email_tools import send_reply_impl

TO = "jessitron@jessitron.com"
SUBJECT = "Cyndibot says hi"
BODY = (
    "This is a smoke test of the send_reply tool against a real\n"
    "verified recipient (not the self-loop).\n"
    "\n"
    "If you're reading this in your inbox, SES outbound to the\n"
    "verified jessitron@jessitron.com identity works end-to-end,\n"
    "and the agent can do the same thing the moment we grant it\n"
    "a real recipient to reply to.\n"
    "\n"
    "— Cyndibot\n"
)
FAKE_IN_REPLY_TO = ""


def main() -> None:
    result = send_reply_impl(
        to=TO,
        subject=SUBJECT,
        body_text=BODY,
        in_reply_to=FAKE_IN_REPLY_TO,
    )
    print("send_reply returned:")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
