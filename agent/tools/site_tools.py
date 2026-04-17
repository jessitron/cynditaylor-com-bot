"""Tools the agent uses to read + edit Cyndi's static site."""

import os
import subprocess
from pathlib import Path
from typing import Any

from strands import tool

WORKSPACE_DIR = Path(
    os.environ.get("CYNDIBOT_WORKSPACE", "cynditaylor-com")
).resolve()
SITE_REPO_URL = os.environ.get(
    "CYNDIBOT_SITE_REPO", "https://github.com/jessitron/cynditaylor-com.git"
)
GIT_USER_NAME = os.environ.get("CYNDIBOT_GIT_USER_NAME", "Cyndibot")
GIT_USER_EMAIL = os.environ.get(
    "CYNDIBOT_GIT_USER_EMAIL", "bot@cyndibot.jessitron.honeydemo.io"
)


def _run_git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd or WORKSPACE_DIR),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _validate_path(rel_path: str) -> Path:
    if rel_path.startswith("/"):
        raise ValueError(f"path must be relative to workspace: {rel_path!r}")
    resolved = (WORKSPACE_DIR / rel_path).resolve()
    try:
        rel = resolved.relative_to(WORKSPACE_DIR)
    except ValueError as exc:
        raise ValueError(f"path escapes workspace: {rel_path!r}") from exc
    if rel.parts and rel.parts[0] == ".git":
        raise ValueError(f"path into .git is forbidden: {rel_path!r}")
    return resolved


def sync_workspace_impl() -> dict[str, Any]:
    if not (WORKSPACE_DIR / ".git").exists():
        WORKSPACE_DIR.parent.mkdir(parents=True, exist_ok=True)
        _run_git(
            "clone",
            SITE_REPO_URL,
            str(WORKSPACE_DIR),
            cwd=WORKSPACE_DIR.parent,
        )
        _run_git("config", "user.name", GIT_USER_NAME)
        _run_git("config", "user.email", GIT_USER_EMAIL)
    else:
        _run_git("fetch", "origin")
        _run_git("reset", "--hard", "origin/main")
        _run_git("clean", "-fd")

    return {
        "workspace": str(WORKSPACE_DIR),
        "head": _run_git("rev-parse", "HEAD").strip(),
    }


def list_site_files_impl() -> list[str]:
    files = []
    for p in WORKSPACE_DIR.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.is_file():
            files.append(str(p.relative_to(WORKSPACE_DIR)))
    return sorted(files)


def read_site_file_impl(path: str) -> str:
    return _validate_path(path).read_text()


def write_site_file_impl(path: str, content: str) -> dict[str, Any]:
    target = _validate_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return {
        "path": str(target.relative_to(WORKSPACE_DIR)),
        "bytes": len(content.encode("utf-8")),
    }


def commit_site_changes_impl(message: str) -> dict[str, Any]:
    _run_git("add", "-A")
    status = _run_git("status", "--porcelain").strip()
    if not status:
        return {"committed": False, "reason": "no changes staged"}
    _run_git("commit", "-m", message)
    return {
        "committed": True,
        "head": _run_git("rev-parse", "HEAD").strip(),
        "files_changed": status,
    }


def push_site_changes_impl(remote_branch: str = "main") -> dict[str, Any]:
    """Push HEAD to origin/<remote_branch>. Defaults to main.

    Relies on the local git credential helper for auth; no token
    plumbing here. On auth failure, git exits non-zero and subprocess
    raises -- the caller sees the original git stderr.
    """
    _run_git("push", "origin", f"HEAD:{remote_branch}")
    return {
        "pushed": True,
        "remote_branch": remote_branch,
        "head": _run_git("rev-parse", "HEAD").strip(),
    }


@tool
def sync_workspace() -> dict[str, Any]:
    """Clone the site repo if needed, then reset it to origin/main.

    Always call this first, before reading or editing any files. It
    discards any prior local changes and returns the current HEAD sha.
    """
    return sync_workspace_impl()


@tool
def list_site_files() -> list[str]:
    """List every tracked and untracked file in the site workspace,
    relative to the workspace root. Excludes .git."""
    return list_site_files_impl()


@tool
def read_site_file(path: str) -> str:
    """Read a single file from the site workspace.

    Args:
        path: Path relative to the workspace root (e.g. "index.html",
            "css/styles.css"). Absolute paths and anything under .git
            are rejected.
    """
    return read_site_file_impl(path)


@tool
def write_site_file(path: str, content: str) -> dict[str, Any]:
    """Overwrite a file in the site workspace with new content.

    Args:
        path: Path relative to the workspace root.
        content: Full new contents of the file.

    Returns:
        Dict with path and bytes written.
    """
    return write_site_file_impl(path, content)


@tool
def commit_site_changes(message: str) -> dict[str, Any]:
    """Stage all changes in the workspace and create a git commit.

    Does NOT push. Use for local edits; a separate push step is needed
    to publish to the live site.

    Args:
        message: Commit message. Should briefly describe what changed
            and why, in human terms.

    Returns:
        Dict with committed (bool), head sha (if committed), and a
        porcelain-format files_changed summary.
    """
    return commit_site_changes_impl(message)


@tool
def push_site_changes() -> dict[str, Any]:
    """Push the local main branch to origin/main. The live site at
    cynditaylor.com will redeploy via GitHub Pages within a minute or so.

    Only call this after commit_site_changes reports committed=True.
    """
    return push_site_changes_impl("main")
