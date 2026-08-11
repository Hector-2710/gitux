"""Domain models for GITZ."""

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class FileStatus:
    """Represents the status of a single file in the working tree."""

    index_status: str       
    worktree_status: str    
    path: str               
    old_path: str | None    

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

    name: str       
    path: str       
    owner: str = "" 

    @property
    def display_name(self) -> str:
        """Human-friendly name for the header."""
        return self.name or "(no name)"


@dataclass(frozen=True)
class HeadSummary:
    """Short hash, subject, and epoch-seconds of the HEAD commit (batched log output)."""

    short_hash: str
    subject: str
    epoch: int


@dataclass(frozen=True)
class FileCounts:
    """Partition of the working-tree file count (conflicts excluded from other buckets)."""

    staged: int
    modified: int
    untracked: int
    conflicts: int

    @classmethod
    def from_status(cls, files: list[FileStatus]) -> "FileCounts":
        """Partition a status list into staged/modified/untracked/conflicts."""

        staged = modified = untracked = conflicts = 0
        for f in files:
            if (
                f.index_status == "U"
                or f.worktree_status == "U"
                or (f.index_status == "A" and f.worktree_status == "A")
                or (f.index_status == "D" and f.worktree_status == "D")
            ):
                conflicts += 1
            elif f.index_status == "?":
                untracked += 1
            elif f.is_staged:
                staged += 1
            elif f.worktree_status != " ":
                modified += 1
            else:
                modified += 1
        return cls(
            staged=staged,
            modified=modified,
            untracked=untracked,
            conflicts=conflicts,
        )


@dataclass(frozen=True)
class OperationState:
    """Merge/rebase in-progress flags from one shared git-dir lookup."""

    merge: bool
    rebase: bool

    @property
    def in_progress(self) -> bool:
        """True if a merge or rebase is currently in progress."""
        return self.merge or self.rebase


class WipState(Enum):
    """Work-in-progress state rendered as a single colored dot on the top bar."""

    UNKNOWN = "unknown"     
    CLEAN = "clean"         
    DIRTY = "dirty"         
    CONFLICT = "conflict"   


def derive_wip_state(file_counts: FileCounts, operation: OperationState | None, has_commits: bool,) -> WipState:
    """Derive the WIP dot state with locked precedence CONFLICT > UNKNOWN > DIRTY > CLEAN."""

    if operation is None:
        return WipState.UNKNOWN
    if operation.in_progress or file_counts.conflicts > 0:
        return WipState.CONFLICT
    if not has_commits:
        return WipState.UNKNOWN
    if (
        file_counts.staged > 0
        or file_counts.modified > 0
        or file_counts.untracked > 0
    ):
        return WipState.DIRTY
    return WipState.CLEAN


@dataclass(frozen=True)
class CommitLogEntry:
    """Represents a single entry in the commit log graph."""

    raw_line: str          


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
