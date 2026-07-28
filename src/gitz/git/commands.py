"""Low-level git command wrappers using subprocess."""

import subprocess
from urllib.parse import urlparse

from gitz.domain import FileStatus, PushResult, RemoteStatus, RepoInfo
from gitz.git.exceptions import GitError
from gitz.git.parser import parse_push_output, parse_status

_TIMEOUT = 30  # seconds for most operations
_PUSH_TIMEOUT = 60  # seconds for push (network I/O)


def _run(args: list[str], *, timeout: int = _TIMEOUT) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result. Raises GitError on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"Git command timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not found on PATH") from exc

    if result.returncode != 0:
        raise GitError(
            f"git {' '.join(args[:3])} failed (exit {result.returncode})",
            stderr=result.stderr.strip(),
        )
    return result


def get_status() -> list[FileStatus]:
    """Return all file statuses using ``git status --porcelain=v1 -z``."""
    result = _run(["status", "--porcelain=v1", "-z"])
    return parse_status(result.stdout)


def stage(paths: list[str]) -> None:
    """Stage files using ``git add``."""
    if not paths:
        return
    _run(["add", "--", *paths])


def unstage(paths: list[str]) -> None:
    """Unstage files using ``git reset HEAD``."""
    if not paths:
        return
    _run(["reset", "HEAD", "--", *paths])


def get_staged_diff() -> str:
    """Return the combined diff of all staged changes."""
    result = _run(["diff", "--cached"])
    return result.stdout


def get_file_diff(path: str) -> str:
    """Return the unstaged diff for a single file."""
    try:
        result = _run(["diff", "--", path])
        return result.stdout
    except GitError:
        return ""


def get_staged_file_diff(path: str) -> str:
    """Return the staged diff for a single file."""
    try:
        result = _run(["diff", "--cached", "--", path])
        return result.stdout
    except GitError:
        return ""


def commit(message: str) -> str:
    """Create a commit with the given message. Returns the short hash."""
    _run(["commit", "-m", message])
    result = _run(["rev-parse", "--short", "HEAD"])
    return result.stdout.strip()


def push(remote: str = "origin", branch: str = "") -> PushResult:
    """Push to remote using ``git push --porcelain``. Returns PushResult."""
    args = ["push", "--porcelain"]
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)

    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=_PUSH_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return PushResult(success=False, error="Push timed out")
    except FileNotFoundError as exc:
        return PushResult(success=False, error=str(exc))

    ok_refs, failed_refs = parse_push_output(result.stdout)

    if result.returncode != 0 and not failed_refs:
        failed_refs.append(("refs/*", result.stderr.strip() or "push failed"))

    return PushResult(
        success=result.returncode == 0,
        pushed_refs=ok_refs,
        failed_refs=failed_refs,
        error=result.stderr.strip() if result.returncode != 0 else None,
    )


def get_current_branch() -> str:
    """Return the name of the current branch."""
    result = _run(["rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def _extract_repo_name(url: str) -> str:
    """Extract the repository name from a remote URL.

    Handles:
        https://github.com/user/gitz.git  →  gitz
        git@github.com:user/gitz.git      →  gitz
        https://github.com/user/gitz      →  gitz
    """
    # Try urlparse first (works for https:// and http://)
    parsed = urlparse(url)
    if parsed.path:
        name = parsed.path.rsplit("/", 1)[-1]
    else:
        # SSH-style: git@github.com:user/repo.git
        name = url.rsplit("/", 1)[-1]

    # Strip trailing .git
    if name.endswith(".git"):
        name = name[:-4]

    return name


def get_repo_info() -> RepoInfo:
    """Return repository identity (name + absolute working-tree path)."""
    # Working tree root
    toplevel = _run(["rev-parse", "--show-toplevel"]).stdout.strip()

    # Try to get remote URL from origin, fallback to first remote
    name = ""
    try:
        url = _run(["remote", "get-url", "origin"]).stdout.strip()
        name = _extract_repo_name(url)
    except GitError:
        # No origin — try any configured remote
        try:
            result = _run(["remote"])
            remotes = result.stdout.strip().splitlines()
            if remotes:
                url = _run(["remote", "get-url", remotes[0]]).stdout.strip()
                name = _extract_repo_name(url)
        except GitError:
            pass

    return RepoInfo(name=name, path=toplevel)


def get_remote_status() -> RemoteStatus:
    """Return ahead/behind counts and tracking info for the current branch."""
    branch = get_current_branch()

    # Try to get tracking branch
    try:
        result = _run([
            "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"
        ])
        upstream = result.stdout.strip()
        remote, _, upstream_branch = upstream.partition("/")
    except GitError:
        return RemoteStatus(remote="", branch=branch, ahead=0, behind=0)

    # Get ahead/behind counts
    try:
        result = _run([
            "rev-list", "--left-right", "--count",
            f"{branch}...{upstream}",
        ])
        counts = result.stdout.strip().split("\t")
        ahead = int(counts[0]) if len(counts) > 0 else 0
        behind = int(counts[1]) if len(counts) > 1 else 0
    except (GitError, ValueError):
        ahead, behind = 0, 0

    return RemoteStatus(
        remote=remote,
        branch=upstream_branch,
        ahead=ahead,
        behind=behind,
    )


def get_branches() -> list[str]:
    """Return list of local branch names from ``git branch``."""
    result = _run(["branch"])
    branches = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    # Clean up: remove leading "* " from current branch
    cleaned = []
    for b in branches:
        if b.startswith("* "):
            cleaned.append(b[2:])
        else:
            cleaned.append(b)
    return cleaned


def get_commit_log(count: int = 30) -> str:
    """Return the commit log with ASCII graph via ``git log --all --oneline --graph --decorate``."""
    result = _run(["log", "--all", "--oneline", "--graph", "--decorate", f"-{count}"])
    return result.stdout


def is_detached_head() -> bool:
    """Return True if HEAD is detached."""
    try:
        _run(["symbolic-ref", "-q", "HEAD"], timeout=5)
        return False
    except GitError:
        return True


def is_merge_in_progress() -> bool:
    """Return True if a merge is in progress."""
    from pathlib import Path

    git_dir = Path(_run(["rev-parse", "--git-dir"]).stdout.strip())
    return (git_dir / "MERGE_HEAD").exists()


def is_rebase_in_progress() -> bool:
    """Return True if a rebase is in progress."""
    from pathlib import Path

    git_dir = Path(_run(["rev-parse", "--git-dir"]).stdout.strip())
    rebase_dir = git_dir / "rebase-merge"
    rebase_apply = git_dir / "rebase-apply"
    return rebase_dir.exists() or rebase_apply.exists()
