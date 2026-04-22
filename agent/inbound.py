import sys

from opentelemetry import trace

from agent.cyndibot import build_agent
from agent.observability import configure_tracing


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m agent.inbound <s3_key>")
    s3_key = sys.argv[1]

    configure_tracing()
    agent = build_agent()
    agent(f"The inbound email is at S3 key: {s3_key}")
    print()

    trace.get_tracer_provider().shutdown()


if __name__ == "__main__":
    main()
