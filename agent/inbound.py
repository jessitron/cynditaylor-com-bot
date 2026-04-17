import sys

from opentelemetry import trace
from strands import Agent
from strands.models import BedrockModel

from agent.observability import configure_tracing
from agent.tools.email_tools import parse_inbound

REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are Cyndibot, an assistant that helps Cyndi update her \
static HTML website by reading emails she sends you.

You will be given an S3 key pointing at a raw email Cyndi sent. Use the \
parse_inbound tool to read it. Then describe, in one short paragraph:
  1. Who sent it.
  2. What they are asking for (be concrete about which page / what change).
  3. Any ambiguity you'd need to resolve before editing the site.

Do not attempt to make any edits yet. Just read and summarize."""


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m agent.inbound <s3_key>")
    s3_key = sys.argv[1]

    configure_tracing()

    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[parse_inbound],
    )

    agent(f"The inbound email is at S3 key: {s3_key}")
    print()

    trace.get_tracer_provider().shutdown()


if __name__ == "__main__":
    main()
