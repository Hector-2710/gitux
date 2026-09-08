"""Shared subprocess runner for git commands."""

import subprocess

from gitux.git.exceptions import GitError

_TIMEOUT = 30


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


def _run_tolerant(
    args: list[str], *, allowed_return_codes: set[int], timeout: int = _TIMEOUT
) -> subprocess.CompletedProcess[str]:
    """Run git, treating allowed_return_codes as success. Raises GitError otherwise."""
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
    if result.returncode not in allowed_return_codes:
        raise GitError(
            f"git {' '.join(args[:3])} failed (exit {result.returncode})",
            stderr=result.stderr.strip(),
        )
    return result