"""Block container — wraps a content widget with a styled header and active state."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static
from textual.widget import Widget


class BlockContainer(Vertical):
    """Bento-grid block that wraps a content widget with a styled title header.

    Supports active/inactive visual states via CSS classes (``.block-active`` /
    ``.block-inactive``) for keyboard focus indication.

    Used to wrap ChangedFilesPanel, CommitLogWidget, and DiffViewerWidget in the
    bento layout.
    """

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        content_widget: Widget | None = None,
        **kwargs,
    ) -> None:
        self._title = title
        self._subtitle = subtitle
        self._content_widget = content_widget
        self._active = False
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Static(self._render_header(), classes="block-header")
        if self._content_widget:
            yield self._content_widget

    def set_active(self, active: bool) -> None:
        """Toggle the active state, which changes the border styling."""
        self._active = active
        self.set_class(active, "block-active")
        self.set_class(not active, "block-inactive")

    def set_header_subtitle(self, subtitle: str) -> None:
        """Update the subtitle text in the block header in-place."""
        self._subtitle = subtitle
        header = self.query_one(".block-header", Static)
        header.update(self._render_header())

    def _render_header(self) -> str:
        if self._subtitle:
            return f"{self._title} / {self._subtitle}"
        return self._title
                