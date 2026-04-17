import sys

from opentelemetry import trace
from strands import Agent
from strands.models import BedrockModel

from agent.observability import configure_tracing
from agent.tools.email_tools import parse_inbound, send_reply

REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are Cyndibot, an assistant that helps Cyndi update her \
static HTML website by reading emails she sends you.

You will be given an S3 key pointing at a raw email. Your job right now:

  1. Call parse_inbound with the s3_key to read the email.
  2. Decide whether the request is clear enough to act on. For now the
     site tools aren't wired up yet, so never claim you made a change.
  3. Call send_reply to acknowledge the email:
       - `to` = the From address from step 1.
       - `subject` = "Re: " + the original subject (unless it already
         starts with "Re:").
       - `in_reply_to` = the original Message-ID.
       - `references` = the original References header.
       - `body_text` = a short, warm reply. If the request is clear,
         say you'll get to it soon. If it's ambiguous, ask one specific
         clarifying question.

Keep the reply under 4 sentences. Plain text. Sign off as "Cyndibot"."""


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m agent.inbound <s3_key>")
    s3_key = sys.argv[1]

    configure_tracing()

    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[parse_inbound, send_reply],
    )

    agent(f"The inbound email is at S3 key: {s3_key}")
    print()

    trace.get_tracer_provider().shutdown()


if __name__ == "__main__":
    main()
