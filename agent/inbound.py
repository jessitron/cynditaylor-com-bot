import sys
import uuid

from opentelemetry import trace

from agent.cyndibot import build_agent
from agent.observability import configure_tracing


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m agent.inbound <s3_key>")
    s3_key = sys.argv[1]

    configure_tracing()
    invocation_id = uuid.uuid4().hex
    thread_id = f"local-{invocation_id}"
    agent = build_agent(thread_id=thread_id)
    tracer = trace.get_tracer("agent.inbound")
    with tracer.start_as_current_span("agent.invocation") as span:
        span.set_attribute("invocation.id", invocation_id)
        agent(f"The inbound email is at S3 key: {s3_key}")
    print()

    trace.get_tracer_provider().shutdown()


if __name__ == "__main__":
    main()
