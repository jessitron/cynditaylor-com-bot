import json
import sys

phoenix_url = sys.argv[1]
project_name = sys.argv[2]
payload = json.load(sys.stdin)

projects = [
    e["node"]
    for e in payload["data"]["projects"]["edges"]
    if e["node"]["name"] == project_name
]
if not projects:
    print(f"project '{project_name}' not found")
    sys.exit(1)

project = projects[0]
project_id = project["id"]
spans = [e["node"] for e in project["spans"]["edges"]]

if not spans:
    print("no spans")
    sys.exit(0)

# Pick the trace id of the most recent span and filter to it.
latest_trace_id = spans[0]["trace"]["traceId"]
trace_spans = [s for s in spans if s["trace"]["traceId"] == latest_trace_id]

print(f"project:   {project['name']}")
print(f"trace id:  {latest_trace_id}")
print(f"trace URL: {phoenix_url}/projects/{project_id}/traces/{latest_trace_id}")
print(f"spans in trace: {len(trace_spans)}")
print()

# Build parent -> children map keyed by spanId.
children: dict[str | None, list[dict]] = {}
for s in trace_spans:
    children.setdefault(s["parentId"], []).append(s)

for bucket in children.values():
    bucket.sort(key=lambda s: s["startTime"])


def walk(parent_id: str | None, depth: int) -> None:
    for span in children.get(parent_id, []):
        indent = "  " * depth
        kind = span.get("spanKind") or "-"
        print(f"{indent}- {span['name']}  [{kind}]  ({span['statusCode']})")
        walk(span["spanId"], depth + 1)


# Root spans: parentId null OR parent not in this trace.
known_ids = {s["spanId"] for s in trace_spans}
roots = [s for s in trace_spans if not s["parentId"] or s["parentId"] not in known_ids]
roots.sort(key=lambda s: s["startTime"])

for root in roots:
    print(f"- {root['name']}  [{root.get('spanKind') or '-'}]  ({root['statusCode']})")
    walk(root["spanId"], 1)
