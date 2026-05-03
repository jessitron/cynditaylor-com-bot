"""Build the environmentVariables JSON map for create-agent-runtime.

Reads from the current process env (which is populated by sourcing .env
and collector/.env in the calling shell script). Prints a JSON object to
stdout.

Traces go to Boswell (the OTel collector Lambda), which adds the
Honeycomb team header on egress. The producer auths to Boswell with a
bearer token; the AgentCore runtime never sees the Honeycomb API key.
"""

import json
import os
import sys

REQUIRED = ("BOSWELL_FUNCTION_URL", "INGEST_BEARER_TOKEN", "OTEL_SERVICE_NAME")


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
        # Trips Strands' is_langfuse heuristic (substring match on "langfuse")
        # so gen_ai.{input,output}.messages land on span attributes for Honeycomb,
        # in addition to the span events the spec mandates. Boswell drops the
        # redundant events on egress; this duplication is harmless and removing
        # the env var is a separate cleanup.
        "LANGFUSE_BASE_URL": "langfuse-stub-for-honeycomb",
        "AWS_REGION": "us-west-2",
        "AWS_DEFAULT_REGION": "us-west-2",
        "CYNDIBOT_WORKSPACE": "/mnt/workspace/cynditaylor-com",
    }

    json.dump(env_vars, sys.stdout)


if __name__ == "__main__":
    main()
