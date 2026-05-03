"""Build the environmentVariables JSON map for create-agent-runtime.

Reads from the current process env (which is populated by sourcing .env
and collector/.env in the calling shell script). Prints a JSON object to
stdout.

Traces go to Boswell (the OTel collector Lambda), which lifts span-event
attrs onto the parent span via OTTL and adds the Honeycomb team header
on egress. The producer auths to Boswell with a bearer token; the
AgentCore runtime never sees the Honeycomb API key. Because Boswell does
the event-to-attribute lift, we don't need to trip Strands' is_langfuse
heuristic on the producer side.
"""

import json
import os
import sys

REQUIRED = (
    "BOSWELL_FUNCTION_URL",
    "INGEST_BEARER_TOKEN",
    "OTEL_SERVICE_NAME",
    "GITHUB_TOKEN_SECRET_ARN",
)


def main() -> None:
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"missing required env vars: {', '.join(missing)}")

    traces_endpoint = os.environ["BOSWELL_FUNCTION_URL"].rstrip("/") + "/v1/traces"

    env_vars = {
        "OTEL_SERVICE_NAME": os.environ["OTEL_SERVICE_NAME"],
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": traces_endpoint,
        "OTEL_EXPORTER_OTLP_HEADERS": (
            f"authorization=Bearer {os.environ['INGEST_BEARER_TOKEN']}"
        ),
        "OTEL_SEMCONV_STABILITY_OPT_IN": "gen_ai_latest_experimental",
        "AWS_REGION": "us-west-2",
        "AWS_DEFAULT_REGION": "us-west-2",
        "CYNDIBOT_WORKSPACE": "/mnt/workspace/cynditaylor-com",
        "GITHUB_TOKEN_SECRET_ARN": os.environ["GITHUB_TOKEN_SECRET_ARN"],
    }

    json.dump(env_vars, sys.stdout)


if __name__ == "__main__":
    main()
