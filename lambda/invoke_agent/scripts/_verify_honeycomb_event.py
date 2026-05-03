"""Assert the dispatcher Lambda sent a Honeycomb event with a given outcome.

Polls CloudWatch for `honeycomb event sent: event_id=<id> outcome=<outcome>`
log lines since the given start-time, prints all of them, and passes if any
match the expected outcome. The full smoke roundtrip generates two invocations
(original inbound → invoked, agent's reply → skipped_recipient_filter), so we
can't just take the first match.

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


def _parse(events: list[dict]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for ev in events:
        m = PATTERN.search(ev.get("message", ""))
        if not m:
            continue
        event_id, outcome = m.group(1), m.group(2)
        if event_id in seen:
            continue
        seen.add(event_id)
        pairs.append((event_id, outcome))
    return pairs


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("log_group")
    p.add_argument("region")
    p.add_argument("since_ms", type=int)
    p.add_argument("expected_outcome")
    p.add_argument("--timeout-s", type=int, default=30)
    args = p.parse_args()

    deadline = time.time() + args.timeout_s
    pairs: list[tuple[str, str]] = []
    while time.time() < deadline:
        pairs = _parse(_filter_log_events(args.log_group, args.region, args.since_ms))
        if any(outcome == args.expected_outcome for _, outcome in pairs):
            break
        time.sleep(2)

    if not pairs:
        print(
            f"FAIL: no 'honeycomb event sent' log line within {args.timeout_s}s "
            f"(log group {args.log_group}, since {args.since_ms})",
            file=sys.stderr,
        )
        return 1

    print(f"events sent ({len(pairs)}):")
    matched = False
    for event_id, outcome in pairs:
        marker = "  *" if outcome == args.expected_outcome and not matched else "   "
        print(f"{marker} event_id={event_id} outcome={outcome}")
        if outcome == args.expected_outcome:
            matched = True

    if not matched:
        print(
            f"FAIL: no event with expected outcome={args.expected_outcome}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
