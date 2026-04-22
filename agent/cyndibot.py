from strands import Agent
from strands.models import BedrockModel

from agent.tools.email_tools import parse_inbound, send_reply
from agent.tools.site_tools import (
    commit_site_changes,
    list_site_files,
    push_site_changes,
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
     - If NO (greeting, test, ambiguous), skip to step 8 and reply
       with a clarifying question.
     - If YES, continue.

  3. Call sync_workspace once. This resets a local clone to origin/main.

  4. Use list_site_files / read_site_file to find or understand the
     file(s) you need. Prefer reading before writing so you preserve
     structure and match the site's existing style (CSS links, header,
     footer, etc).

  5. Call write_site_file with the full new contents of each file you
     change.

  6. Changelog convention. A file `changelog.html` at the repo root
     records every change. If it doesn't exist yet, create it with the
     same CSS link as other pages; no nav link should point to it.
     Add a new entry to changelog.html for THIS change: include the
     date (parsed from the email's `date` field, formatted as YYYY-MM-DD)
     and a short description. Do NOT invent a date -- always use the
     one from parse_inbound. If the sender's email local part starts
     with `pretend-` or `smoketest-`, prefix the entry with `[TEST]`
     so real changes and test changes are distinguishable.

  7. Call commit_site_changes, then push_site_changes. This publishes
     the change to the live site via GitHub Pages.

  8. Call send_reply:
       - `to` = the From address from step 1.
       - `subject` = "Re: " + the original subject (unless it starts
         with "Re:" already).
       - `in_reply_to` = the original Message-ID.
       - `references` = the original References header.
       - `body_text` = short, warm. Describe what you changed (or what
         you need clarified). Sign off as "Cyndibot".

Keep the reply under 5 sentences. Plain text only."""


def build_agent() -> Agent:
    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    return Agent(
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
            push_site_changes,
        ],
    )
