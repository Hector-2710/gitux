"""Git-related exceptions."""


class GitError(Exception):
    """Raised when a git command fails."""

    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr
