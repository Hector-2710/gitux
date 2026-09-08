"""Working-tree status, staging, and diff commands."""

from gitux.domain import FileStatus
from gitux.git.exceptions import GitError
from gitux.git.parser import parse_status
from gitux.git.runner import _run, _run_tolerant


def get_status() -> list[FileStatus]:
    """Return all file statuses using ``git status --porcelain=v1 -z -uall``.

    ``-uall`` expands untracked directories so every file is listed
    individually — never a collapsed ``dir/`` entry.
    """
    result = _run(["status", "--porcelain=v1", "-z", "-uall"])
    return parse_status(result.stdout)


def stage(paths: list[str]) -> None:
    """Stage files using ``git add``."""
    if not paths:
        return
    _run(["add", "--", *paths])


def unstage(paths: list[str]) -> None:
    """Unstage files using ``git reset HEAD``."""
    if not paths:
        return
    _run(["reset", "HEAD", "--", *paths])


def get_staged_diff() -> str:
    """Return the combined diff of all staged changes."""
    result = _run(["diff", "--cached"])
    return result.stdout


def get_file_diff(path: str) -> str:
    """Return the unstaged diff for a single file."""
    try:
        result = _run(["diff", "--", path])
        return result.stdout
    except GitError:
        return ""


def get_staged_file_diff(path: str) -> str:
    """Return the staged diff for a single file."""
    try:
        result = _run(["diff", "--cached", "--", path])
        return result.stdout
    except GitError:
        return ""


def get_untracked_file_diff(path: str) -> str:
    """Unified diff of an untracked file vs /dev/null; "" for binary or empty files."""
    try:
        result = _run_tolerant(
            ["diff", "--no-index", "/dev/null", path], allowed_return_codes={0, 1},
        )
    except GitError:
        return ""
    if any(line.startswith("Binary files ") for line in result.stdout.splitlines()):
        return ""
    if not any(line.startswith("@@") for line in result.stdout.splitlines()):
        return ""
    return result.stdout