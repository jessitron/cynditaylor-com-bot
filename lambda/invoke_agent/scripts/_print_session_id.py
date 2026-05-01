"""Print the runtimeSessionId the dispatcher Lambda would compute for a given email.

Useful to verify session stability or to look up a session in Honeycomb without
having to read it out of CloudWatch logs.

Usage:
    python scripts/_print_session_id.py <email-address>
"""

from __future__ import annotations

import hashlib
import sys


def session_id(addr: str) -> str:
    digest = hashlib.sha256(addr.lower().encode("utf-8")).hexdigest()
    return f"mom-{digest}"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: _print_session_id.py <email-address>")
    print(session_id(sys.argv[1]))


if __name__ == "__main__":
    main()
