"""Branch-related git commands."""

from gitux.git.exceptions import GitError
from gitux.git.runner import _run


def get_current_branch() -> str:
    """Return the name of the current branch.

    Empty repo -> "main" (exit 0); detached HEAD -> "" (exit 0).
    """
    result = _run(["branch", "--show-current"])
    return result.stdout.strip()


def get_branches() -> list[str]:
    """Return list of local branch names from ``git branch``."""
    result = _run(["branch"])
    branches = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    cleaned = []
    for b in branches:
        name = b[2:] if b.startswith("* ") else b
        if name.startswith("("):
            continue
        cleaned.append(name)
    return cleaned


def switch_branch(name: str) -> None:
    """Switch to a local branch via ``git switch``. Raises GitError on failure."""
    _run(["switch", name])


def is_detached_head() -> bool:
    """Return True if HEAD is detached."""
    try:
        _run(["symbolic-ref", "-q", "HEAD"], timeout=5)
        return False
    except GitError:
        return True


def get_default_branch() -> str:
    """Return the default branch name from a single ``git branch -r`` call.

    Parses stripped lines in order: an ``origin/HEAD -> origin/<name>`` line wins;
    otherwise the ``origin/main``/``origin/master`` convention; else ``""``.
    Never mutates, never touches the network.
    """
    result = _run(["branch", "-r"])
    lines = [line.strip() for line in result.stdout.splitlines()]
    for line in lines:
        if line.startswith("origin/HEAD") and " -> " in line:
            target = line.split(" -> ", 1)[-1].strip()
            if target.startswith("origin/"):
                return target[len("origin/"):]
    if "origin/main" in lines:
        return "main"
    if "origin/master" in lines:
        return "master"
    return ""