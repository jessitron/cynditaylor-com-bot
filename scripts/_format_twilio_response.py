import json
import sys

raw = sys.stdin.read().rstrip("\n")
body_text, _, status_line = raw.rpartition("\n")
if not status_line.startswith("HTTP "):
    body_text, status_line = raw, ""

try:
    body = json.loads(body_text)
    print(json.dumps(body, indent=2))
except json.JSONDecodeError:
    print(body_text)

if status_line:
    print(status_line)

# Twilio success statuses are 200 or 201.
status_code = ""
if status_line.startswith("HTTP "):
    status_code = status_line.split()[1]
if status_code not in ("200", "201"):
    sys.exit(1)
