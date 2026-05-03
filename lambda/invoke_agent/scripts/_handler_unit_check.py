"""Quick local check that handler.py parses CYNDIBOT_AGENT_USERNAMES correctly.

Sets the minimum required env vars (so handler module imports), then asserts
the alias set + matcher behave as expected. Doesn't talk to AWS.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    os.environ["CYNDIBOT_AGENT_RUNTIME_ARN"] = (
        "arn:aws:bedrock-agentcore:us-west-2:414852377253:runtime/x"
    )
    os.environ["CYNDIBOT_AGENT_USERNAMES"] = "cyndi,bot,robot,jeeves"
    os.environ["CYNDIBOT_AGENT_DOMAIN"] = "cyndibot.jessitron.honeydemo.io"
    os.environ["HONEYCOMB_API_KEY"] = "dummy"

    here = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(here))
    import handler

    expected_usernames = {"cyndi", "bot", "robot", "jeeves"}
    assert handler.AGENT_USERNAMES == expected_usernames, handler.AGENT_USERNAMES

    expected_recipients = {f"{u}@cyndibot.jessitron.honeydemo.io" for u in expected_usernames}
    assert handler.AGENT_RECIPIENTS == expected_recipients, handler.AGENT_RECIPIENTS

    m = handler._matched_agent_recipient(
        ["Foo@example.com", "BOT@cyndibot.jessitron.honeydemo.io"]
    )
    assert m == "bot@cyndibot.jessitron.honeydemo.io", m

    m = handler._matched_agent_recipient(["stranger@cyndibot.jessitron.honeydemo.io"])
    assert m is None, m

    m = handler._matched_agent_recipient(["jeeves@cyndibot.jessitron.honeydemo.io"])
    assert m == "jeeves@cyndibot.jessitron.honeydemo.io", m

    print("handler unit check: PASS")
    print(f"  AGENT_USERNAMES = {sorted(handler.AGENT_USERNAMES)}")
    print(f"  AGENT_RECIPIENTS = {sorted(handler.AGENT_RECIPIENTS)}")


if __name__ == "__main__":
    main()
