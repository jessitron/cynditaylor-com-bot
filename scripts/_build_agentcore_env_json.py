"""Build the environmentVariables JSON map for create-agent-runtime.

Reads from the current process env (which is populated by sourcing .env
in the calling shell script). Prints a JSON object to stdout.
"""

import json
import os
import sys

REQUIRED = ("HONEYCOMB_API_KEY", "OTEL_SERVICE_NAME")


def main() -> None:
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"missing required env vars: {', '.join(missing)}")

    env_vars = {
        "OTEL_SERVICE_NAME": os.environ["OTEL_SERVICE_NAME"],
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "https://api.honeycomb.io/v1/traces",
        "OTEL_EXPORTER_OTLP_HEADERS": (
            f"x-honeycomb-team={os.environ['HONEYCOMB_API_KEY']}"
        ),
        "AWS_REGION": "us-west-2",
        "AWS_DEFAULT_REGION": "us-west-2",
        "CYNDIBOT_WORKSPACE": "/mnt/workspace/cynditaylor-com",
    }

    json.dump(env_vars, sys.stdout)


if __name__ == "__main__":
    main()
