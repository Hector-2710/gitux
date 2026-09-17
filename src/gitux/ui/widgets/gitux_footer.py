"""Application footer — shows version, keyboard shortcuts, and sync status."""

from rich.text import Text
from textual.widgets import Static

from gitux import __version__


class GituxFooter(Static):
    """Bottom status bar with version info, keybinding hints, and sync indicator.

    Layout:
    - Version tag (e.g. ``GITUX v1.0.4``)
    - List of common keyboard shortcuts
    - Sync status icon (✓ / ✗)
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._sync_ok: bool = True

    def on_mount(self) -> None:
        """Render the footer on initial mount."""
        self._refresh()

    def update_sync(self, ok: bool = True) -> None:
        """Update the sync indicator display."""
        self._sync_ok = ok
        self._refresh()

    def _refresh(self) -> None:
        """Re-render the footer content from the current state."""
        t = Text()

        t.append(f" GITUX v{__version__} \u2502", style="bold #06B6D4")
        t.append("[?] Help", style="#06B6D4")

        sync_icon = "\u2713" if self._sync_ok else "\u2717"  # ✓ / ✗
        sync_style = "bold #34d399" if self._sync_ok else "bold #f87171"
        t.append(f" \u2502 {sync_icon} sync", style=sync_style)

        self.update(t)
