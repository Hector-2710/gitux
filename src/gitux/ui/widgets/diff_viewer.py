"""Diff viewer widget — shows unified diffs with line numbers."""

import re
from typing import Self, override

from rich.text import Text
from textual.widgets import RichLog

_MAX_DIFF_LINES: int = 2000

_COLORS: dict[str, str] = {
    "addition": "#10b981",
    "addition_bg": "#123a2a",
    "deletion": "#ffb4ab",
    "deletion_bg": "#3a1d1d",
    "header": "#9c60ec",
    "default": "#e4e1ed",
    "dim": "#c7c4d7",
    "line_num": "#4a3a6b",
}

_DIFF_METADATA_PREFIXES: tuple[str, ...] = (
    "diff --",
    "index ",
    "--- ",
    "+++ ",
    "new file mode ",
    "deleted file mode ",
    "old mode ",
    "new mode ",
    "copy from ",
    "copy to ",
    "rename from ",
    "rename to ",
    "similarity index ",
    "dissimilarity index ",
)


def _is_diff_metadata(line: str) -> bool:
    """Return True if ``line`` is git diff metadata (``diff --``, ``index``, ...)."""
    return line.startswith(_DIFF_METADATA_PREFIXES)


def _parse_hunk_header(line: str) -> tuple[int, int]:
    """Parse @@ -old_start,old_count +new_start,new_count @@.

    Returns (old_start, new_start).
    """
    match = re.search(r"\-(\d+)", line)
    old_start = int(match.group(1)) if match else 0
    match = re.search(r"\+(\d+)", line)
    new_start = int(match.group(1)) if match else 0
    return old_start, new_start


def _format_gutter(old: int | None, new: int | None) -> str:
    """Format the line-number gutter.

    Shows a single line number: new for context/added lines, old for
    deleted lines. The hunk header (``@@ -old +new @@``) carries the
    overall old→new mapping.
    """
    num = new if new is not None else old
    return f"{num:>5} │ "


class DiffViewerWidget(RichLog):
    """Displays unified diffs with line numbers and semantic coloring.

    Shows:
        - Hunk headers (@@ ... @@) in primary color
        - Added lines (+) in green with new file line number
        - Removed lines (-) in red with old file line number
        - Context lines in default with both line numbers
        - Git metadata headers are hidden (redundant)
    """

    can_focus = False

    def __init__(self, **kwargs) -> None:
        super().__init__(
            highlight=False, markup=False, auto_scroll=False, max_lines=None, **kwargs
        )
        self._current_diff: str = ""

    def show_diff(self, diff_text: str) -> None:
        """Display a unified diff with line numbers and truncation."""
        self._current_diff = diff_text
        if not diff_text:
            self._show_placeholder("Select a file to view diff")
            return

        lines = diff_text.splitlines()
        total = len(lines)

        if total > _MAX_DIFF_LINES:
            lines = lines[:_MAX_DIFF_LINES]
            truncated = True
        else:
            truncated = False

        text = Text()
        old_lineno = 0
        new_lineno = 0

        for line in lines:
            if line.startswith("@@"):
                old_lineno, new_lineno = _parse_hunk_header(line)
                text.append(f"  {line}\n", style=_COLORS["header"])
            elif _is_diff_metadata(line):
                # diff --git, index, ---, +++, modes, renames... hidden.
                continue
            elif line.startswith("\\"):
                # \ No newline at end of file — special marker, no counter advance.
                text.append(f"  {line}\n", style=f"italic {_COLORS['dim']}")
            elif line.startswith("+"):
                content = line[1:]
                text.append(
                    _format_gutter(None, new_lineno) + f"+{content}\n",
                    style=f"{_COLORS['addition']} on {_COLORS['addition_bg']}",
                )
                new_lineno += 1
            elif line.startswith("-"):
                content = line[1:]
                text.append(
                    _format_gutter(old_lineno, None) + f"-{content}\n",
                    style=f"{_COLORS['deletion']} on {_COLORS['deletion_bg']}",
                )
                old_lineno += 1
            else:
                content = line[1:] if line.startswith(" ") else line
                text.append(
                    _format_gutter(old_lineno, new_lineno) + f" {content}\n",
                    style=_COLORS["default"],
                )
                old_lineno += 1
                new_lineno += 1

        if truncated:
            text.append(
                f"\n  [{_MAX_DIFF_LINES} of {total} lines shown]",
                style=f"italic {_COLORS['dim']}",
            )

        super().clear()
        self.write(text)
        self.scroll_home(animate=False)

    def show_binary_placeholder(self) -> None:
        """Show placeholder for binary files."""
        self._show_placeholder("Binary file, no diff available")

    def show_no_diff_placeholder(self) -> None:
        """Show placeholder when no diff is available (empty file, error)."""
        self._show_placeholder("No diff available")

    @override
    def clear(self) -> Self:
        """Clear the diff display."""
        self._current_diff = ""
        return self._show_placeholder("Select a file to view diff")

    def _show_placeholder(self, message: str) -> Self:
        """Show a dim placeholder message and scroll to top."""
        super().clear()
        self.write(Text(f"  {message}", style=f"italic {_COLORS['dim']}"))
        self.scroll_home(animate=False)
        return self