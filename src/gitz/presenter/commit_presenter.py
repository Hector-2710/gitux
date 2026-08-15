"""Presenter for working-tree operations: status, staging, commit, push."""

from gitz.domain import CommitResult, FileStatus, PushResult
from gitz.git import (
    GitError,
    commit as git_commit,
    get_file_diff,
    get_operation_state,
    get_remote_status,
    get_staged_diff,
    get_staged_file_diff,
    get_status,
    get_untracked_file_diff,
    is_detached_head,
    push as git_push,
    stage as git_stage,
    unstage as git_unstage,
)


class CommitPresenter:
    """Business logic for viewing status, staging, committing, and pushing."""

    def __init__(self) -> None:
        self._status: list[FileStatus] = []

    def load_status(self) -> list[FileStatus]:
        """Load and return current file statuses."""
        self._status = get_status()
        return self._status

    @property
    def staged_files(self) -> list[FileStatus]:
        """Files with staged changes."""
        return [f for f in self._status if f.is_staged]

    @property
    def unstaged_files(self) -> list[FileStatus]:
        """Files with unstaged changes (including untracked)."""
        return [f for f in self._status if f.is_unstaged]

    def stage_files(self, paths: list[str]) -> None:
        """Stage the given file paths."""
        git_stage(paths)

    def unstage_files(self, paths: list[str]) -> None:
        """Unstage the given file paths."""
        git_unstage(paths)

    def get_diff(self, file_status: FileStatus) -> str:
        """Get diff for a file."""
        if file_status.is_staged:
            return get_staged_file_diff(file_status.path)
        if file_status.index_status == "?" or file_status.worktree_status == "?":
            return get_untracked_file_diff(file_status.path)
        return get_file_diff(file_status.path)

    def get_staged_preview(self) -> str:
        """Get combined diff of all staged changes."""
        return get_staged_diff()

    def commit(self, message: str) -> CommitResult:
        """Create a commit with the given message after validation."""
        cleaned = self._clean_message(message)
        if not cleaned:
            return CommitResult(success=False, error="Commit message cannot be empty")

        if not self.staged_files:
            return CommitResult(success=False, error="No staged changes to commit")

        try:
            commit_hash = git_commit(cleaned)
            return CommitResult(success=True, commit_hash=commit_hash)
        except GitError as exc:
            return CommitResult(success=False, error=str(exc))

    def push(self) -> PushResult:
        """Push committed changes to remote."""
        status = get_remote_status()
        if not status.remote:
            return PushResult(success=False, error="No remote configured")
        if status.behind > 0:
            return PushResult(
                success=False,
                error="Remote has new changes. Pull first.",
            )

        return git_push(remote=status.remote, branch=status.branch)

    def can_commit(self) -> bool:
        """Whether commit action is allowed."""
        state = get_operation_state()               
        if is_detached_head() or state.in_progress:  
            return False
        return len(self.staged_files) > 0

    def can_push(self) -> bool:
        """Whether push action is allowed."""
        status = get_remote_status()
        return status.remote != "" and status.ahead > 0

    @staticmethod
    def _clean_message(message: str) -> str:
        """Clean commit message: strip, remove comment lines."""
        lines = message.strip().splitlines()
        cleaned = [line for line in lines if not line.lstrip().startswith("#")]
        return "\n".join(cleaned).strip()
