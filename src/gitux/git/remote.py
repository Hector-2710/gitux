"""Remote, push, and repository-identity commands."""

import subprocess
from pathlib import Path
from urllib.parse import urlparse

from gitux.domain import PushResult, RemoteStatus, RepoInfo
from gitux.git.branch import get_current_branch
from gitux.git.exceptions import GitError
from gitux.git.parser import parse_push_output
from gitux.git.runner import _run

_PUSH_TIMEOUT = 60


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


def _extract_repo_name(url: str) -> str:
    """Extract the repository name from a remote URL."""
    parsed = urlparse(url)
    if parsed.path:
        name = parsed.path.rsplit("/", 1)[-1]
    else:
        name = url.rsplit("/", 1)[-1]

    if name.endswith(".git"):
        name = name[:-4]

    return name


def _extract_owner(url: str) -> str:
    """Extract the repository owner from a remote URL."""
    parsed = urlparse(url)
    if parsed.scheme in ("https", "http"):
        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) >= 2:
            return segments[-2]
        return ""

    if ":" in url:
        path_part = url.rsplit(":", 1)[-1]
        segments = [s for s in path_part.split("/") if s]
        if len(segments) >= 2:
            return segments[-2]
    return ""


def get_repo_info() -> RepoInfo:
    """Return repository identity (name + owner + absolute working-tree path)."""
    toplevel = _run(["rev-parse", "--show-toplevel"]).stdout.strip()

    name = ""
    owner = ""
    try:
        url = _run(["remote", "get-url", "origin"]).stdout.strip()
        name = _extract_repo_name(url)
        owner = _extract_owner(url)
    except GitError:
        try:
            result = _run(["remote"])
            remotes = result.stdout.strip().splitlines()
            if remotes:
                url = _run(["remote", "get-url", remotes[0]]).stdout.strip()
                name = _extract_repo_name(url)
                owner = _extract_owner(url)
        except GitError:
            pass

    if not name and toplevel:
        name = Path(toplevel).name

    return RepoInfo(name=name, path=toplevel, owner=owner)


def get_remote_status() -> RemoteStatus:
    """Return ahead/behind counts and tracking info for the current branch."""
    branch = get_current_branch()

    try:
        result = _run([
            "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"
        ])
        upstream = result.stdout.strip()
        remote, _, upstream_branch = upstream.partition("/")
    except GitError:
        return RemoteStatus(remote="", branch=branch, ahead=0, behind=0)

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