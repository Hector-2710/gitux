"""Changed files panel — staged/unstaged file list with cursor navigation."""

from collections.abc import Callable

from rich.text import Text
from textual.widgets import RichLog

from gitux.domain import FileStatus


_STATUS_COLORS: dict[str, str] = {
    "M": "#ffb783",
    "A": "#10b981",
    "D": "#ffb4ab",
    "R": "#06B6D4",
    "C": "#06B6D4",
    "u": "#22c55e",
    "!": "#c7c4d7",
}

_MAX_PATH_CHARS: int = 40


class ChangedFilesPanel(RichLog):
    """File listing panel with staged and unstaged sections."""

    can_focus = False

    def __init__(self, **kwargs) -> None:
        super().__init__(
            highlight=False, markup=False, auto_scroll=False, max_lines=None, **kwargs
        )
        self._files: list[FileStatus] = []
        self._cursor_index: int = 0
        self._on_toggle: Callable[[FileStatus], None] | None = None
        self._on_selection_change: Callable[[], None] | None = None
        self._on_stage_all: Callable[[], None] | None = None
        self._on_unstage_all: Callable[[], None] | None = None

    @property
    def selected_file(self) -> FileStatus | None:
        """Return the :class:`FileStatus` under the cursor, or ``None``."""
        all_files = self._all_files_flat
        if 0 <= self._cursor_index < len(all_files):
            return all_files[self._cursor_index]
        return None

    @property
    def _all_files_flat(self) -> list[FileStatus]:
        """Staged files followed by unstaged files, in cursor order."""
        staged = [f for f in self._files if f.is_staged]
        unstaged = [f for f in self._files if f.is_unstaged]
        return staged + unstaged

    def set_files(self, files: list[FileStatus]) -> None:
        """Replace the file list and reset cursor if out of bounds."""
        self._files = files
        total = len(self._all_files_flat)
        if self._cursor_index >= total:
            self._cursor_index = max(0, total - 1)
        self._refresh_content()
        self._scroll_to_cursor()

    def set_on_toggle(self, callback: Callable[[FileStatus], None]) -> None:
        """Register a callback invoked when the user toggles a file's staged state."""
        self._on_toggle = callback

    def set_on_selection_change(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when the cursor moves to a different file."""
        self._on_selection_change = callback

    def set_on_stage_all(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when the user triggers stage-all."""
        self._on_stage_all = callback

    def set_on_unstage_all(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when the user triggers unstage-all."""
        self._on_unstage_all = callback

    def action_cursor_down(self) -> None:
        """Move cursor down to the next file in the flat list."""
        all_files = self._all_files_flat
        if self._cursor_index < len(all_files) - 1:
            self._cursor_index += 1
            self._refresh_content()
            self._scroll_to_cursor()
            if self._on_selection_change:
                self._on_selection_change()

    def action_cursor_up(self) -> None:
        """Move cursor up to the previous file in the flat list."""
        if self._cursor_index > 0:
            self._cursor_index -= 1
            self._refresh_content()
            self._scroll_to_cursor()
            if self._on_selection_change:
                self._on_selection_change()

    def action_toggle_file(self) -> None:
        """Stage or unstage the file under the cursor."""
        file = self.selected_file
        if file and self._on_toggle:
            self._on_toggle(file)

    def action_stage_all(self) -> None:
        """Stage all currently unstaged files."""
        if self._on_stage_all:
            self._on_stage_all()

    def action_unstage_all(self) -> None:
        """Unstage all currently staged files."""
        if self._on_unstage_all:
            self._on_unstage_all()

    def _refresh_content(self) -> None:
        """Clear the widget and re-render the full file list."""
        _ = self.clear()
        _ = self.write(self._render_files())

    def _render_files(self) -> Text:
        """Build the full layout with STAGED and UNSTAGED sections."""
        text = Text(no_wrap=True)
        staged = [f for f in self._files if f.is_staged]
        unstaged = [f for f in self._files if f.is_unstaged]

        text.append(" \u25a0 STAGED", style="bold #06B6D4")
        text.append("\n")

        if staged:
            text.append(self._build_file_entries(staged, 0))
        else:
            text.append("   No changed files\n", style="italic #c7c4d7")

        text.append(" \u25a0 UNSTAGED", style="bold #ffb783")
        text.append("\n")

        if unstaged:
            text.append(self._build_file_entries(unstaged, len(staged)))
        else:
            text.append("   No changed files\n", style="italic #c7c4d7")

        return text

    def _build_file_entries(self, files: list[FileStatus], start_index: int) -> Text:
        """Build rich text entries for a slice of files, marking the cursor row."""
        text = Text()
        for i, f in enumerate(files):
            linear_idx = start_index + i
            is_cursor = linear_idx == self._cursor_index
            status = f.display_status
            color = _STATUS_COLORS.get(status, "#e4e1ed")

            if is_cursor:
                text.append(" \u276f", style="bold #9c60ec")
            else:
                text.append("  ")

            text.append(f" {status}", style=f"bold {color}")
            text.append(f" {self._truncate_path(f.display_path)}", style="#e4e1ed")
            text.append("\n")

        return text

    def _truncate_path(self, display_path: str) -> str:
        """Truncate a rendered path to ``_MAX_PATH_CHARS`` with a trailing ``..``."""
        if len(display_path) > _MAX_PATH_CHARS:
            return display_path[:_MAX_PATH_CHARS - 2] + ".."
        return display_path

    def _row_for_index(self, index: int) -> int:
        """Rendered-line offset of flat cursor ``index`` (accounts for section headers)."""
        all_files = self._all_files_flat
        if not all_files:
            return 0
        staged_count = len([f for f in self._files if f.is_staged])
        if index < staged_count:
            return 1 + index
        if staged_count > 0:
            return index + 2
        return index + 3

    def _scroll_to_cursor(self) -> None:
        """Ensure the cursor row is visible; no-op when the file list is empty."""
        if not self._all_files_flat:
            return
        target = 0 if self._cursor_index == 0 else self._row_for_index(self._cursor_index)
        self.scroll_to(y=target, animate=False)
