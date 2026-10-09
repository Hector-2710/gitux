"""Presenter for repository-level operations (branch, remote, repo info).

A pure pass-through layer (structure T4: no silent failures): expected
states (empty repo, no upstream) are handled by the git layer with sentinel
values; real failures raise ``GitError`` and surface as error states in the
UI — never as empty data.
"""

from gitux.domain import HeadSummary, OperationState, RemoteStatus, RepoInfo
from gitux.git import (
    create_branch as git_create_branch,
    delete_branch as git_delete_branch,
    get_branches as git_get_branches,
    get_commit_details as git_get_commit_details,
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
    merge_branch as git_merge_branch,
    switch_branch as git_switch_branch,
)


class RepoPresenter:
    """Business logic for repository queries — branch, remote, identity, log.

    Every method propagates ``GitError`` on real git failures; the UI layer
    routes those to the persistent error line (skeleton K2).
    """

    def get_current_branch(self) -> str:
        """Return the current branch name. Raises GitError on failure."""
        return get_current_branch()

    def is_detached_head(self) -> bool:
        """Return True if HEAD is detached. Raises GitError on failure."""
        return is_detached_head()

    def get_remote_status(self) -> RemoteStatus:
        """Get ahead/behind status; ``remote=""`` when no upstream (expected).

        Raises GitError on real failures.
        """
        return get_remote_status()

    def get_repo_info(self) -> RepoInfo:
        """Get repository identity (name + path). Raises GitError on failure."""
        return get_repo_info()

    def get_commit_log(self, count: int = 30) -> str:
        """Return the ASCII commit log graph; "" for an empty repository.

        Raises GitError on real failures.
        """
        return git_get_commit_log(count)

    def get_commit_details(self, commit_hash: str) -> str:
        """Return commit detail text (hash/author/date/subject/body/stat).

        Raises GitError on failure.
        """
        return git_get_commit_details(commit_hash)

    def get_branches(self) -> list[str]:
        """Return local branch names. Raises GitError on failure."""
        return git_get_branches()

    def switch_branch(self, name: str) -> None:
        """Switch to a local branch. Propagates GitError to the caller."""
        git_switch_branch(name)

    def create_branch(self, name: str) -> None:
        """Create a local branch (skeleton K3). Propagates GitError."""
        git_create_branch(name)

    def delete_branch(self, name: str) -> None:
        """Delete a local branch (safe -d, skeleton K3). Propagates GitError."""
        git_delete_branch(name)

    def merge_branch(self, name: str) -> str:
        """Merge a branch into the current one (skeleton K3). Propagates GitError."""
        return git_merge_branch(name)

    def get_user(self) -> str:
        """Return the configured git user. Raises GitError on failure."""
        return git_get_user()

    def get_head_summary(self) -> HeadSummary | None:
        """Return the HEAD commit summary, or None for an empty repository.

        Raises GitError on real failures.
        """
        return git_get_head_summary()

    def get_default_branch(self) -> str:
        """Return the default branch name. Raises GitError on failure."""
        return git_get_default_branch()

    def get_operation_state(self) -> OperationState:
        """Return the merge/rebase operation state. Raises GitError on failure."""
        return git_get_operation_state()

    def is_merge_in_progress(self) -> bool:
        """Return True if a merge is in progress. Raises GitError on failure."""
        return git_is_merge_in_progress()

    def is_rebase_in_progress(self) -> bool:
        """Return True if a rebase is in progress. Raises GitError on failure."""
        return git_is_rebase_in_progress()
