"""Commit-related git commands."""

from gitux.domain import HeadSummary
from gitux.git.exceptions import GitError
from gitux.git.runner import _run

_COMMIT_DETAILS_FORMAT = "%h %an <%ae>%n%ad%n%n%s%n%n%b"

_EMPTY_REPO_MARKER = "does not have any commits yet"


def commit(message: str) -> str:
    """Create a commit with the given message. Returns the short hash."""
    _run(["commit", "-m", message])
    result = _run(["rev-parse", "--short", "HEAD"])
    return result.stdout.strip()


def get_commit_log(count: int = 30) -> str:
    """Return the commit log with ASCII graph via ``git log --all --oneline --graph --decorate``.

    Returns ``""`` for an empty repository (an expected state, not an error).
    ``GitError`` propagates for real failures (structure T4: no silent errors).
    """
    try:
        result = _run(["log", "--all", "--oneline", "--graph", "--decorate", f"-{count}"])
    except GitError as exc:
        if _EMPTY_REPO_MARKER in exc.stderr:
            return ""
        raise
    return result.stdout


def get_commit_details(commit_hash: str) -> str:
    """Return commit metadata + --stat summary via `git show`. Raises GitError on failure."""
    result = _run([
        "show", f"--format={_COMMIT_DETAILS_FORMAT}", "--stat", "--date=iso", commit_hash,
    ])
    return result.stdout


def get_head_summary() -> HeadSummary | None:
    """Return short hash, subject, and epoch of HEAD, or None when malformed.

    Returns ``None`` for an empty repository (an expected state, not an
    error). ``GitError`` propagates for real failures (structure T4).
    """
    try:
        result = _run(["log", "-1", "--format=%h%x09%s%x09%ct"])
    except GitError as exc:
        if _EMPTY_REPO_MARKER in exc.stderr:
            return None
        raise
    parts = result.stdout.strip().split("\t")
    if len(parts) < 3:
        return None
    try:
        epoch = int(parts[2])
    except ValueError:
        return None
    return HeadSummary(short_hash=parts[0], subject=parts[1], epoch=epoch)