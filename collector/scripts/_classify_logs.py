"""Read CloudWatch events as a JSON array of message strings, group, tally."""

import json
import sys
from collections import Counter


def category(line: str) -> str:
    if "INFO app is not ready" in line:
        return "LWA: app-not-ready poll"
    if "EXTENSION\tName: lambda-adapter" in line:
        return "Lambda: extension state"
    if line.startswith("INIT_REPORT"):
        return "Lambda: INIT_REPORT"
    if line.startswith("START RequestId"):
        return "Lambda: START"
    if line.startswith("END RequestId"):
        return "Lambda: END"
    if line.startswith("REPORT RequestId"):
        return "Lambda: REPORT"
    if "Starting otelcol-contrib" in line:
        return "Collector: startup banner"
    if "Starting extensions" in line:
        return "Collector: starting extensions"
    if "Extension is starting" in line or "Extension started" in line:
        return "Collector: extension lifecycle"
    if "Starting HTTP server" in line:
        return "Collector: HTTP receiver up"
    if "Everything is ready" in line:
        return "Collector: ready"
    if "alias is deprecated" in line:
        return "Collector: deprecation warning"
    if "ottl@" in line and "parser_collection" in line:
        return "Collector: OTTL path-rewrite info"
    return "OTHER"


def main() -> None:
    data = json.load(sys.stdin)
    counts: Counter[str] = Counter()
    for ln in data:
        counts[category(ln)] += 1

    total = sum(counts.values())
    print(f"\nTotal log entries in window: {total}")
    print()
    for cat, n in counts.most_common():
        print(f"  {n:4d}  {cat}")


if __name__ == "__main__":
    main()
