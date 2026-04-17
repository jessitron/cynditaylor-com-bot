import sys

from opentelemetry import trace
from strands import Agent
from strands.models import BedrockModel

from agent.observability import configure_tracing
from agent.tools.email_tools import parse_inbound, send_reply
from agent.tools.site_tools import (
    commit_site_changes,
    list_site_files,
    read_site_file,
    sync_workspace,
    write_site_file,
)

REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are Cyndibot, an assistant that helps Cyndi update her \
static HTML website at github.com/jessitron/cynditaylor-com by acting on \
emails she sends you.

You will be given an S3 key pointing at a raw email. Workflow:

  1. Call parse_inbound with the s3_key to read the email.

  2. Decide: is this a concrete request to change the website?
     - If NO (greeting, test, ambiguous), skip steps 3-5 and just
       reply with a clarifying question.
     - If YES, continue.

  3. Call sync_workspace once. This resets a local clone to origin/main.

  4. Use list_site_files / read_site_file to find the file you need to
     change. Prefer reading before writing so you preserve structure.

  5. Call write_site_file with the full new contents of the file.

  6. Call commit_site_changes with a clear, human-readable message.
     Pushing is a separate step and is NOT wired up yet, so the commit
     is local only -- mention this in your reply.

  7. Call send_reply:
       - `to` = the From address from step 1.
       - `subject` = "Re: " + the original subject (unless it starts
         with "Re:" already).
       - `in_reply_to` = the original Message-ID.
       - `references` = the original References header.
       - `body_text` = short, warm. Describe what you changed (or what
         you need clarified). Note that the change is a local commit
         not yet published. Sign off as "Cyndibot".

Keep the reply under 5 sentences. Plain text only."""


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m agent.inbound <s3_key>")
    s3_key = sys.argv[1]

    configure_tracing()

    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            parse_inbound,
            send_reply,
            sync_workspace,
            list_site_files,
            read_site_file,
            write_site_file,
            commit_site_changes,
        ],
    )

    agent(f"The inbound email is at S3 key: {s3_key}")
    print()

    trace.get_tracer_provider().shutdown()


if __name__ == "__main__":
    main()
