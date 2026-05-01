"""Print each log line on its own row, prefixed with its index.

CloudWatch's REPORT entries have internal tabs between fields (one CloudWatch
event = one logical line), so split only on newlines. We also use --output
json on the AWS CLI side to avoid tab-as-record-separator surprises.
"""

import json
import sys


def main() -> None:
    data = json.load(sys.stdin)
    for i, ln in enumerate(data, 1):
        compact = ln.rstrip().replace("\t", " ⇥ ")
        print(f"[{i:3d}] {compact[:200]}")


if __name__ == "__main__":
    main()
