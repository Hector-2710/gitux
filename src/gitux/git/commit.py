"""Commit-related git commands."""

from gitux.domain import HeadSummary
from gitux.git.runner import _run

_COMMIT_DETAILS_FORMAT = "%h %an <%ae>%n%ad%n%n%s%n%n%b"


def commit(message: str) -> str:
    """Create a commit with the given message. Returns the short hash."""
    _run(["commit", "-m", message])
    result = _run(["rev-parse", "--short", "HEAD"])
    return result.stdout.strip()


def get_commit_log(count: int = 30) -> str:
    """Return the commit log with ASCII graph via ``git log --all --oneline --graph --decorate``."""
    result = _run(["log", "--all", "--oneline", "--graph", "--decorate", f"-{count}"])
    return result.stdout


def get_commit_details(commit_hash: str) -> str:
    """Return commit metadata + --stat summary via `git show`. Raises GitError on failure."""
    result = _run([
        "show", f"--format={_COMMIT_DETAILS_FORMAT}", "--stat", "--date=iso", commit_hash,
    ])
    return result.stdout


def get_head_summary() -> HeadSummary | None:
    """Return short hash, subject, and epoch of HEAD, or None when malformed.

    ``GitError`` propagates for empty repos (exit 128) — the presenter converts.
    """
    result = _run(["log", "-1", "--format=%h%x09%s%x09%ct"])
    parts = result.stdout.strip().split("\t")
    if len(parts) < 3:
        return None
    try:
        epoch = int(parts[2])
    except ValueError:
        return None
    return HeadSummary(short_hash=parts[0], subject=parts[1], epoch=epoch)