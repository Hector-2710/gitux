"""Repository state commands (git dir, in-progress operations)."""

from pathlib import Path

from gitux.domain import OperationState
from gitux.git.runner import _run


def get_git_dir() -> str:
    """Return the git directory path via ``git rev-parse --git-dir``."""
    return _run(["rev-parse", "--git-dir"]).stdout.strip()


def get_operation_state() -> OperationState:
    """Return merge/rebase in-progress flags from one shared git-dir lookup."""
    git_dir = Path(get_git_dir())
    return OperationState(
        merge=(git_dir / "MERGE_HEAD").exists(),
        rebase=(git_dir / "rebase-merge").exists()
        or (git_dir / "rebase-apply").exists(),
    )


def is_merge_in_progress() -> bool:
    """Return True if a merge is in progress."""
    return (Path(get_git_dir()) / "MERGE_HEAD").exists()


def is_rebase_in_progress() -> bool:
    """Return True if a rebase is in progress."""
    git_dir = Path(get_git_dir())
    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()