"""Build the exact MIME bytes we would send via SES (without actually
sending). Useful for diagnosing From/Reply-To rewriting suspicions.
"""

from email.message import EmailMessage

from agent.tools.email_tools import REPLY_FROM


def main() -> None:
    msg = EmailMessage()
    msg["From"] = REPLY_FROM
    msg["To"] = "jessitron@jessitron.com"
    msg["Subject"] = "example"
    msg.set_content("body")

    raw = msg.as_bytes()
    print("=== raw MIME we hand to SES ===")
    print(raw.decode("utf-8"))


if __name__ == "__main__":
    main()
