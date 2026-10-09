"""Error line — persistent contextual error strip (skeleton K2, structure T3).

A single-line Static at the bottom of the board, hidden unless an error
exists. Carries what happened + the next action + its key; clears on the
next action. Replaces auto-dismiss toasts for errors (UX-003).
"""

from textual.widgets import Static

_ERROR_SYMBOL = "\u2717"  # ⨯ — the error symbol (surface V5)


class ErrorLine(Static):
    """Persistent error line: shows what happened and the way forward."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.display = False

    def show(self, message: str) -> None:
        """Show an error message (format per T3: what happened → next action + key)."""
        self.update(f" {_ERROR_SYMBOL} {message}")
        self.display = True

    def clear(self) -> None:
        """Hide the error line."""
        self.update("")
        self.display = False
