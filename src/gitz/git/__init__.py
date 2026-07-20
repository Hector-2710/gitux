"""Git infrastructure layer — subprocess wrappers and porcelain parsing."""

from gitz.git.exceptions import GitError
from gitz.git.commands import (
    commit,
    get_current_branch,
    get_file_diff,
    get_remote_status,
    get_repo_info,
    get_staged_diff,
    get_staged_file_diff,
    get_status,
    is_detached_head,
    is_merge_in_progress,
    is_rebase_in_progress,
    push,
    stage,
    unstage,
)

__all__ = [
    "GitError",
    "commit",
    "get_current_branch",
    "get_file_diff",
    "get_remote_status",
    "get_repo_info",
    "get_staged_diff",
    "get_staged_file_diff",
    "get_status",
    "is_detached_head",
    "is_merge_in_progress",
    "is_rebase_in_progress",
    "push",
    "stage",
    "unstage",
]
