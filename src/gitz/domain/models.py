"""Domain models for GITZ."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FileStatus:
    """Represents the status of a single file in the working tree."""

    index_status: str       # X from porcelain: M, A, D, R, C, ?, !
    worktree_status: str    # Y from porcelain: M, D, ?, space
    path: str               # File path relative to repo root
    old_path: str | None    # Original path for renames/copies

    @property
    def is_staged(self) -> bool:
        """True if file has staged changes (index_status is not space or ?)."""
        return self.index_status not in (" ", "?")

    @property
    def is_unstaged(self) -> bool:
        """True if file has unstaged changes or is untracked."""
        return self.worktree_status != " "

    @property
    def display_status(self) -> str:
        """Return the primary status character for display."""
        if self.index_status not in (" ", "?"):
            return self.index_status
        return self.worktree_status

    @property
    def display_path(self) -> str:
        """Return formatted path, including old->new for renames."""
        if self.old_path:
            return f"{self.old_path} -> {self.path}"
        return self.path


@dataclass(frozen=True)
class CommitResult:
    """Result of a git commit operation."""

    success: bool
    commit_hash: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class PushResult:
    """Result of a git push operation."""

    success: bool
    pushed_refs: list[str] = field(default_factory=list)
    failed_refs: list[tuple[str, str]] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class RepoInfo:
    """Repository identity extracted from the local clone."""

    name: str       # e.g. "gitz" (last segment of remote URL)
    path: str       # absolute path to the working tree root

    @property
    def display_name(self) -> str:
        """Human-friendly name for the header."""
        return self.name or "(no name)"


@dataclass(frozen=True)
class RemoteStatus:
    """Current remote tracking status for the active branch."""

    remote: str
    branch: str
    ahead: int
    behind: int

    @property
    def diverged(self) -> bool:
        """True if both ahead > 0 and behind > 0."""
        return self.ahead > 0 and self.behind > 0
