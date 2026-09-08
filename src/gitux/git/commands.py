"""Backward-compatible re-exports of the git command wrappers.

The wrappers were split into domain modules (``runner``, ``status``, ``commit``,
``branch``, ``remote``, ``repo``, ``config``) to reduce per-file complexity.
This module exists only so that ``from gitux.git.commands import ...`` keeps
working; prefer importing from ``gitux.git`` directly.
"""

from gitux.git.branch import (
    get_branches,
    get_current_branch,
    get_default_branch,
    is_detached_head,
    switch_branch,
)
from gitux.git.commit import (
    _COMMIT_DETAILS_FORMAT,
    commit,
    get_commit_details,
    get_commit_log,
    get_head_summary,
)
from gitux.git.config import (
    _os_login,
    _try_config,
    get_user,
)
from gitux.git.remote import (
    _extract_owner,
    _extract_repo_name,
    _PUSH_TIMEOUT,
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
from gitux.git.runner import (
    _TIMEOUT,
    _run,
    _run_tolerant,
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
    "_COMMIT_DETAILS_FORMAT",
    "_PUSH_TIMEOUT",
    "_TIMEOUT",
    "_extract_owner",
    "_extract_repo_name",
    "_os_login",
    "_run",
    "_run_tolerant",
    "_try_config",
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