"""Parse the files modified in the thread-scoped-session slice.

Pure syntax check — does not import, so works without the agent's runtime
deps installed. Used by the slice's smoke flow to fail fast if any file
got mangled while editing.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

FILES = [
    "lambda/invoke_agent/handler.py",
    "agent/server.py",
    "agent/observability.py",
    "agent/inbound.py",
    "agent/tools/email_tools.py",
]


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    failed = False
    for rel in FILES:
        path = repo_root / rel
        try:
            ast.parse(path.read_text())
            print(f"OK  {rel}")
        except SyntaxError as exc:
            print(f"ERR {rel}: {exc}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
