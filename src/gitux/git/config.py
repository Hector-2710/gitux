"""Git user configuration commands."""

import os

from gitux.git.exceptions import GitError
from gitux.git.runner import _run


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