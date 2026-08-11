"""Presenter for repository-level operations (branch, remote, repo info)."""

from gitz.domain import HeadSummary, OperationState, RemoteStatus, RepoInfo
from gitz.git import (
    GitError,
    get_branches as git_get_branches,
    get_current_branch,
    get_commit_log as git_get_commit_log,
    get_default_branch as git_get_default_branch,
    get_head_summary as git_get_head_summary,
    get_operation_state as git_get_operation_state,
    get_remote_status,
    get_repo_info,
    get_user as git_get_user,
    is_detached_head,
    is_merge_in_progress as git_is_merge_in_progress,
    is_rebase_in_progress as git_is_rebase_in_progress,
    switch_branch as git_switch_branch,
)


class RepoPresenter:
    """Business logic for repository queries — branch, remote, identity, log. """

    def get_current_branch(self) -> str:
        """Return current branch name, or empty string on error."""
        try:
            return get_current_branch()
        except GitError:
            return ""

    def is_detached_head(self) -> bool:
        """Return True if HEAD is detached, or False on error."""
        try:
            return is_detached_head()
        except GitError:
            return False

    def get_remote_status(self) -> RemoteStatus | None:
        """Get ahead/behind status for current branch, or None on error."""
        try:
            return get_remote_status()
        except GitError:
            return None

    def get_repo_info(self) -> RepoInfo | None:
        """Get repository identity (name + path), or None on error."""
        try:
            return get_repo_info()
        except GitError:
            return None

    def get_commit_log(self, count: int = 30) -> str:
        """Return the ASCII commit log graph, or empty string on error."""
        try:
            return git_get_commit_log(count)
        except GitError:
            return ""

    def get_branches(self) -> list[str]:
        """Return local branch names, or [] on error."""
        try:
            return git_get_branches()
        except GitError:
            return []

    def switch_branch(self, name: str) -> None:
        """Switch to a local branch. Propagates GitError to the caller."""
        git_switch_branch(name)

    def get_user(self) -> str:
        """Return the configured git user, or "" on error."""
        try:
            return git_get_user()
        except GitError:
            return ""

    def get_head_summary(self) -> HeadSummary | None:
        """Return the HEAD commit summary, or None on error."""
        try:
            return git_get_head_summary()
        except GitError:
            return None

    def get_default_branch(self) -> str:
        """Return the default branch name, or "" on error."""
        try:
            return git_get_default_branch()
        except GitError:
            return ""

    def get_operation_state(self) -> OperationState | None:
        """Return the merge/rebase operation state, or None on error."""
        try:
            return git_get_operation_state()
        except GitError:
            return None

    def is_merge_in_progress(self) -> bool:
        """Return True if a merge is in progress, or False on error."""
        try:
            return git_is_merge_in_progress()
        except GitError:
            return False

    def is_rebase_in_progress(self) -> bool:
        """Return True if a rebase is in progress, or False on error."""
        try:
            return git_is_rebase_in_progress()
        except GitError:
            return False
