import json
import sys

phoenix_url = sys.argv[1]
payload = json.load(sys.stdin)

for edge in payload["data"]["projects"]["edges"]:
    node = edge["node"]
    name = node["name"]
    project_id = node["id"]
    trace_count = node["traceCount"]

    print(f"project: {name}  (traces: {trace_count})")

    for span_edge in node["spans"]["edges"]:
        span = span_edge["node"]
        trace_id = span["trace"]["traceId"]
        url = f"{phoenix_url}/projects/{project_id}/traces/{trace_id}"
        print(f"  last span: {span['name']}  [{span['statusCode']}]  {span['startTime']}")
        print(f"  trace URL: {url}")
    print()
