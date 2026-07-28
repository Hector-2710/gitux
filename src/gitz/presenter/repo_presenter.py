"""Presenter for repository-level operations (branch, remote, repo info)."""

from gitz.domain import RemoteStatus, RepoInfo
from gitz.git import (
    GitError,
    get_current_branch,
    get_commit_log as git_get_commit_log,
    get_remote_status,
    get_repo_info,
    is_detached_head,
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
