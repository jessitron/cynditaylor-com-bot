"""Smoke test for push_site_changes_impl.

Pushes HEAD to a throwaway branch on origin (NOT main), verifies the
branch exists by asking git ls-remote, then deletes the branch. No
live-site impact (GitHub Pages only watches main).

Uses whatever git credentials the local environment already has (macOS
keychain / gh credential helper). Prints enough detail to diagnose auth
failures without blowing up the output on the happy path.
"""

import subprocess
import sys

from agent.tools.site_tools import (
    WORKSPACE_DIR,
    _run_git,
    commit_site_changes_impl,
    push_site_changes_impl,
    sync_workspace_impl,
    write_site_file_impl,
)

SMOKE_BRANCH = "cyndibot-smoke-test"
SMOKE_FILE = ".cyndibot-smoke"


def remote_has_branch(branch: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch],
        cwd=str(WORKSPACE_DIR),
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(result.stdout.strip())


def delete_remote_branch(branch: str) -> None:
    _run_git("push", "origin", "--delete", branch)


def main() -> None:
    print("1. sync_workspace")
    info = sync_workspace_impl()
    print(f"   HEAD before: {info['head']}")

    print(f"2. stage trivial edit: {SMOKE_FILE}")
    write_site_file_impl(SMOKE_FILE, "cyndibot push smoke test\n")
    commit_info = commit_site_changes_impl("cyndibot push smoke test")
    if not commit_info["committed"]:
        raise SystemExit(f"commit failed: {commit_info}")
    print(f"   committed: {commit_info['head']}")

    print(f"3. push HEAD -> origin/{SMOKE_BRANCH}")
    push_info = push_site_changes_impl(SMOKE_BRANCH)
    print(f"   pushed: {push_info}")

    print("4. verify branch landed on origin")
    if not remote_has_branch(SMOKE_BRANCH):
        raise SystemExit(f"smoke branch {SMOKE_BRANCH} not visible on origin")
    print(f"   origin/{SMOKE_BRANCH} exists ✓")

    print("5. cleanup: delete remote branch")
    delete_remote_branch(SMOKE_BRANCH)
    if remote_has_branch(SMOKE_BRANCH):
        raise SystemExit(f"failed to delete origin/{SMOKE_BRANCH}")
    print(f"   origin/{SMOKE_BRANCH} deleted ✓")

    print()
    print("push auth works. The main-branch push_site_changes tool is safe to call.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\ngit command failed: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"stderr:\n{e.stderr}", file=sys.stderr)
        raise SystemExit(e.returncode)
