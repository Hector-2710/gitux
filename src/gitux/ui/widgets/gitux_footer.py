"""Application footer — shows version, keyboard shortcuts, encoding, and sync status."""

from rich.text import Text
from textual.widgets import Static

from gitux import __version__


class GituxFooter(Static):
    """Bottom status bar with version info, keybinding hints, and sync indicator.

    Layout:
    - Version tag (e.g. ``GITUX v1.0.4``)
    - List of common keyboard shortcuts
    - File encoding
    - Sync status icon (✓ / ✗)
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)

    def on_mount(self) -> None:
        """Render the footer on initial mount."""
        self._refresh()

    def update_sync(self, ok: bool = True, encoding: str = "UTF-8") -> None:
        """Update the sync indicator and encoding display."""
        self._refresh()

    def _refresh(self) -> None:
        """Re-render the footer content from the current state."""
        t = Text()

        t.append(f" GITUX v{__version__} \u2502", style="bold #c7c4d7")
        t.append(" [C] Commit [P] Push [R] Refresh [L] Log [S] Stage [A] Stage All [B] Branches [?] Help [Q] Quit", style="#b7c8e1")

        self.update(t)
