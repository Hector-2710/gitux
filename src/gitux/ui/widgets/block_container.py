"""Block container — wraps a content widget with a styled header and active state."""

from typing import override

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static


class BlockContainer(Vertical):
    """Bento-grid block that wraps a content widget with a styled title header.

    Supports active/inactive visual states via CSS classes (``.block-active`` /
    ``.block-inactive``) for keyboard focus indication.

    Used to wrap ChangedFilesPanel, CommitLogWidget, and DiffViewerWidget in the
    bento layout.
    """

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        content_widget: Widget | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._title: str = title
        self._subtitle: str = subtitle
        self._content_widget: Widget | None = content_widget
        self._active: bool = False
        _ = self.set_class(True, "block-inactive")

    @override
    def compose(self) -> ComposeResult:
        """Yield the header static and the wrapped content widget."""
        yield Static(self._render_header(), classes="block-header")
        if self._content_widget:
            yield self._content_widget

    def set_active(self, active: bool) -> None:
        """Toggle the active state, which changes the border styling."""
        self._active = active
        _ = self.set_class(active, "block-active")
        _ = self.set_class(not active, "block-inactive")

    def set_header_subtitle(self, subtitle: str) -> None:
        """Update the subtitle text in the block header in-place."""
        self._subtitle = subtitle
        header = self.query_one(".block-header", Static)
        header.update(self._render_header())

    def _render_header(self) -> str:
        """Render the header line: ``Title / subtitle`` or subtitle alone."""
        if self._title and self._subtitle:
            return f"{self._title} / {self._subtitle}"
        return self._subtitle or self._title
