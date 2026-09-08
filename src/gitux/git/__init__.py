"""Git infrastructure layer."""

from gitux.git.exceptions import GitError
from gitux.git.branch import (
    get_branches,
    get_current_branch,
    get_default_branch,
    is_detached_head,
    switch_branch,
)
from gitux.git.commit import (
    commit,
    get_commit_details,
    get_commit_log,
    get_head_summary,
)
from gitux.git.config import get_user
from gitux.git.remote import (
    get_remote_status,
    get_repo_info,
    push,
)
from gitux.git.repo import (
    get_git_dir,
    get_operation_state,
    is_merge_in_progress,
    is_rebase_in_progress,
)
from gitux.git.status import (
    get_file_diff,
    get_staged_diff,
    get_staged_file_diff,
    get_status,
    get_untracked_file_diff,
    stage,
    unstage,
)

__all__ = [
    "GitError",
    "commit",
    "get_branches",
    "get_commit_details",
    "get_commit_log",
    "get_current_branch",
    "get_default_branch",
    "get_file_diff",
    "get_git_dir",
    "get_head_summary",
    "get_operation_state",
    "get_remote_status",
    "get_repo_info",
    "get_staged_diff",
    "get_staged_file_diff",
    "get_status",
    "get_untracked_file_diff",
    "get_user",
    "is_detached_head",
    "is_merge_in_progress",
    "is_rebase_in_progress",
    "push",
    "stage",
    "switch_branch",
    "unstage",
]