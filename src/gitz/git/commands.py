"""Low-level git command wrappers using subprocess."""

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from gitz.domain import FileStatus, HeadSummary, OperationState, PushResult, RemoteStatus, RepoInfo
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
    """Return the name of the current branch.

    Empty repo -> "main" (exit 0); detached HEAD -> "" (exit 0).
    """
    result = _run(["branch", "--show-current"])
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


def _extract_owner(url: str) -> str:
    """Extract the repository owner from a remote URL.

    Handles:
        https://github.com/Hector-2710/gitz.git  ->  Hector-2710   (urlparse path)
        git@github.com:user/repo.git             ->  user          (":" split)
        https://gitlab.com/group/subgroup/repo.git -> subgroup    (second-to-last segment)
        fewer than 2 segments                    ->  ""
    """
    parsed = urlparse(url)
    if parsed.scheme in ("https", "http"):
        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) >= 2:
            return segments[-2]
        return ""

    # SSH-style: git@github.com:user/repo.git
    if ":" in url:
        path_part = url.rsplit(":", 1)[-1]
        segments = [s for s in path_part.split("/") if s]
        if len(segments) >= 2:
            return segments[-2]
    return ""


def get_repo_info() -> RepoInfo:
    """Return repository identity (name + owner + absolute working-tree path)."""
    # Working tree root
    toplevel = _run(["rev-parse", "--show-toplevel"]).stdout.strip()

    # Try to get remote URL from origin, fallback to first remote
    name = ""
    owner = ""
    try:
        url = _run(["remote", "get-url", "origin"]).stdout.strip()
        name = _extract_repo_name(url)
        owner = _extract_owner(url)
    except GitError:
        # No origin — try any configured remote
        try:
            result = _run(["remote"])
            remotes = result.stdout.strip().splitlines()
            if remotes:
                url = _run(["remote", "get-url", remotes[0]]).stdout.strip()
                name = _extract_repo_name(url)
                owner = _extract_owner(url)
        except GitError:
            pass

    # No remote name — fall back to the working tree root basename
    if not name and toplevel:
        name = Path(toplevel).name

    return RepoInfo(name=name, path=toplevel, owner=owner)


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
        name = b[2:] if b.startswith("* ") else b
        if name.startswith("("):
            continue
        cleaned.append(name)
    return cleaned


def switch_branch(name: str) -> None:
    """Switch to a local branch via ``git switch``. Raises GitError on failure."""
    _run(["switch", name])


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


def _try_config(key: str) -> str:
    """Return a git config value, or "" on any git error."""
    try:
        return _run(["config", "--get", key]).stdout.strip()
    except GitError:
        return ""


def _os_login() -> str:
    """Return the OS login name, falling back to $USER on failure."""
    try:
        return os.getlogin()
    except OSError:
        return os.environ.get("USER", "")


def get_user() -> str:
    """Return the configured git user (name -> email -> OS login). Never raises."""
    name = _try_config("user.name")
    if name:
        return name
    email = _try_config("user.email")
    if email:
        return email
    return _os_login()


def get_head_summary() -> HeadSummary | None:
    """Return short hash, subject, and epoch of HEAD, or None when malformed.

    ``GitError`` propagates for empty repos (exit 128) — the presenter converts.
    """
    result = _run(["log", "-1", "--format=%h%x09%s%x09%ct"])
    parts = result.stdout.strip().split("\t")
    if len(parts) < 3:
        return None
    try:
        epoch = int(parts[2])
    except ValueError:
        return None
    return HeadSummary(short_hash=parts[0], subject=parts[1], epoch=epoch)


def get_default_branch() -> str:
    """Return the default branch name from a single ``git branch -r`` call.

    Parses stripped lines in order: an ``origin/HEAD -> origin/<name>`` line wins;
    otherwise the ``origin/main``/``origin/master`` convention; else ``""``.
    Never mutates, never touches the network.
    """
    result = _run(["branch", "-r"])
    lines = [line.strip() for line in result.stdout.splitlines()]
    for line in lines:
        if line.startswith("origin/HEAD") and " -> " in line:
            target = line.split(" -> ", 1)[-1].strip()
            if target.startswith("origin/"):
                return target[len("origin/"):]
    if "origin/main" in lines:
        return "main"
    if "origin/master" in lines:
        return "master"
    return ""


def get_git_dir() -> str:
    """Return the git directory path via ``git rev-parse --git-dir``."""
    return _run(["rev-parse", "--git-dir"]).stdout.strip()


def get_operation_state() -> OperationState:
    """Return merge/rebase in-progress flags from one shared git-dir lookup."""
    git_dir = Path(get_git_dir())
    return OperationState(
        merge=(git_dir / "MERGE_HEAD").exists(),
        rebase=(git_dir / "rebase-merge").exists()
        or (git_dir / "rebase-apply").exists(),
    )


def is_merge_in_progress() -> bool:
    """Return True if a merge is in progress."""
    return (Path(get_git_dir()) / "MERGE_HEAD").exists()


def is_rebase_in_progress() -> bool:
    """Return True if a rebase is in progress."""
    git_dir = Path(get_git_dir())
    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()
