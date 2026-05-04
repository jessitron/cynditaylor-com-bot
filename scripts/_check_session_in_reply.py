"""Verify that send_reply appends the session ID footer when one is set.

Stubs boto3 so no email is actually sent — captures the raw MIME and
prints the body so you can eyeball the footer.
"""

import email
from email import policy

import agent.observability as obs
import agent.tools.site_tools as site_tools
from agent.tools import email_tools


class _FakeSES:
    def __init__(self):
        self.last_raw: bytes | None = None

    def send_email(self, Content):
        self.last_raw = Content["Raw"]["Data"]
        return {"MessageId": "fake-message-id"}


def _run(label: str, session_id: str | None, pushed_sha: str | None) -> None:
    fake = _FakeSES()
    orig = email_tools.boto3.client
    email_tools.boto3.client = lambda *a, **kw: fake  # type: ignore[assignment]
    obs._SESSION_ID = session_id
    site_tools._LAST_PUSHED_SHA = pushed_sha
    try:
        email_tools.send_reply_impl(
            to="jessitron@jessitron.com",
            subject="test",
            body_text="hi mom\n\nlove,\nCyndibot",
        )
    finally:
        email_tools.boto3.client = orig

    msg = email.message_from_bytes(fake.last_raw, policy=policy.default)
    body = msg.get_body(preferencelist=("plain",)).get_content()
    print(f"=== {label} (session_id={session_id!r}, pushed_sha={pushed_sha!r}) ===")
    print(body)
    print()


def main() -> None:
    _run("session + push", "abc123-session", "deadbeefcafebabefeedface1234567890abcdef")
    _run("session, no push", "abc123-session", None)
    _run("no session, no push (loud on both)", None, None)


if __name__ == "__main__":
    main()
