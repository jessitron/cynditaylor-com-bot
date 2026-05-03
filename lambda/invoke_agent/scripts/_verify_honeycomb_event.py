"""Assert the dispatcher Lambda sent a Honeycomb event after the most recent invoke.

Polls CloudWatch for a `honeycomb event sent: event_id=<id> outcome=<outcome>`
log line emitted since the given start-time, asserts the outcome matches what
the smoke caller expected, and prints `event_id=<id>` on success so the caller
(and the Honeycomb MCP) can look up that exact row.

Usage:
    _verify_honeycomb_event.py <log-group> <region> <since-millis> <expected-outcome> [--timeout-s N]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time

PATTERN = re.compile(r"honeycomb event sent: event_id=(\S+) outcome=(\S+)")


def _filter_log_events(log_group: str, region: str, since_ms: int) -> list[dict]:
    proc = subprocess.run(
        [
            "aws", "logs", "filter-log-events",
            "--region", region,
            "--log-group-name", log_group,
            "--start-time", str(since_ms),
            "--filter-pattern", "honeycomb event sent",
            "--output", "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    try:
        return json.loads(proc.stdout).get("events") or []
    except json.JSONDecodeError:
        return []


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("log_group")
    p.add_argument("region")
    p.add_argument("since_ms", type=int)
    p.add_argument("expected_outcome")
    p.add_argument("--timeout-s", type=int, default=30)
    args = p.parse_args()

    deadline = time.time() + args.timeout_s
    while time.time() < deadline:
        for ev in _filter_log_events(args.log_group, args.region, args.since_ms):
            m = PATTERN.search(ev.get("message", ""))
            if not m:
                continue
            event_id, outcome = m.group(1), m.group(2)
            if outcome != args.expected_outcome:
                print(
                    f"FAIL: honeycomb event outcome={outcome}, expected {args.expected_outcome}",
                    file=sys.stderr,
                )
                print(f"event_id={event_id}", file=sys.stderr)
                return 1
            print(f"event_id={event_id}")
            print(f"outcome={outcome}")
            return 0
        time.sleep(2)

    print(
        f"FAIL: no 'honeycomb event sent' log line within {args.timeout_s}s "
        f"(log group {args.log_group}, since {args.since_ms})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
