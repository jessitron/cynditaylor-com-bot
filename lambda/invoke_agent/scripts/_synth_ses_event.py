"""Print a JSON SES Lambda event for testing the dispatcher in isolation.

Usage:
    python scripts/_synth_ses_event.py <sender> <recipient> [message_id]

Real SES events have many more fields; we emit just the ones the handler
reads (mail.commonHeaders.from, mail.source, mail.messageId,
receipt.recipients), which is enough for allowlist + recipient-filter
checks. The Lambda is invoked via `aws lambda invoke`, not via SES, so
there's no need for a real S3 object behind the messageId — the handler
short-circuits before touching S3 when the sender is denied.
"""

from __future__ import annotations

import json
import sys
import uuid


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: _synth_ses_event.py <sender> <recipient> [message_id]"
        )
    sender = sys.argv[1]
    recipient = sys.argv[2]
    message_id = sys.argv[3] if len(sys.argv) > 3 else uuid.uuid4().hex

    event = {
        "Records": [
            {
                "eventSource": "aws:ses",
                "eventVersion": "1.0",
                "ses": {
                    "mail": {
                        "messageId": message_id,
                        "source": sender,
                        "destination": [recipient],
                        "commonHeaders": {
                            "from": [sender],
                            "to": [recipient],
                            "subject": "synthetic deny-path test",
                        },
                    },
                    "receipt": {
                        "recipients": [recipient],
                        "spamVerdict": {"status": "PASS"},
                        "virusVerdict": {"status": "PASS"},
                        "spfVerdict": {"status": "PASS"},
                        "dkimVerdict": {"status": "PASS"},
                        "dmarcVerdict": {"status": "PASS"},
                    },
                },
            }
        ]
    }
    print(json.dumps(event))


if __name__ == "__main__":
    main()
