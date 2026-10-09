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


def create_branch(name: str) -> None:
    """Create a local branch via ``git branch`` (scope S2 / skeleton K3).

    Raises GitError on failure (invalid name, duplicate).
    """
    _run(["branch", name])


def delete_branch(name: str) -> None:
    """Delete a local branch via ``git branch -d`` (skeleton K3).

    The safe ``-d`` refuses to delete unmerged branches — the error ladder's
    prevention rung (structure T3) at the git level. Raises GitError on
    failure.
    """
    _run(["branch", "-d", name])


def merge_branch(name: str) -> str:
    """Merge a branch into the current one via ``git merge --no-edit`` (K3).

    Returns git's output. Raises GitError on failure or conflict — the UI
    names the way forward (resolve conflicts, then commit).
    """
    result = _run(["merge", "--no-edit", name])
    return result.stdout


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