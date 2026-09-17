"""Commit log widget — renders ``git log --oneline --graph --decorate`` output."""

from typing import Self, override

from rich.text import Text
from textual.widgets import RichLog

_GRAPH_CHARS: str = "*|/\\ -_`"


def extract_commit_hash(line: str) -> str | None:
    """First hex token after the graph prefix, or None for graph-only lines."""
    for i, ch in enumerate(line):
        if ch not in _GRAPH_CHARS:
            line = line[i:]
            break
    token = line.split(" ", 1)[0] if line else ""
    if len(token) >= 7 and all(c in "0123456789abcdef" for c in token):
        return token
    return None


class CommitLogWidget(RichLog):
    """Displays the git commit graph with ASCII art, refs, and cursor navigation.

    Parses the output of ``git log --all --oneline --graph --decorate`` and renders:
    - Graph lines (``|``, ``/``, ``\\``) in secondary colours
    - Commit nodes (``*``) in primary colour
    - Branch/tag refs (``(...)``) in accent colour
    - Commit hashes and messages in default text
    """

    can_focus = False

    def __init__(self, **kwargs) -> None:
        super().__init__(
            highlight=False, markup=False, auto_scroll=False, max_lines=None, **kwargs
        )
        self._log_lines: list[str] = []
        self._cursor_index: int = 0
        self._detail_hash: str | None = None
        self._detail_text: str | None = None
        _ = self.write(Text("  (loading...)", style="italic #c7c4d7"))

    @property
    def is_detail_mode(self) -> bool:
        """True while a commit detail view is shown instead of the log."""
        return self._detail_hash is not None

    @property
    def cursor_line(self) -> str | None:
        """The raw graph line under the cursor, or None when the log is empty."""
        if 0 <= self._cursor_index < len(self._log_lines):
            return self._log_lines[self._cursor_index]
        return None

    def show_details(self, commit_hash: str, text: str) -> None:
        """Enter detail mode: render `text` (raw) and scroll to top."""
        self._detail_hash = commit_hash
        self._detail_text = text
        self._refresh_content()
        _ = self.scroll_home(animate=False)

    def exit_details(self) -> None:
        """Leave detail mode and restore the log at the cursor."""
        self._detail_hash = None
        self._detail_text = None
        self._refresh_content()
        self._scroll_to_cursor()

    def show_log(self, log_text: str) -> None:
        """Set the log text from raw git output, resetting cursor if needed."""
        self._detail_hash = None
        self._detail_text = None
        if not log_text:
            _ = self.clear()
            return

        self._log_lines = log_text.splitlines()
        if self._cursor_index >= len(self._log_lines):
            self._cursor_index = max(0, len(self._log_lines) - 1)
        self._refresh_content()

    @override
    def clear(self) -> Self:
        """Clear the log and show an empty-state placeholder."""
        self._detail_hash = None
        self._detail_text = None
        self._log_lines = []
        self._cursor_index = 0
        _ = super().clear()
        _ = self.write(Text("  No commits yet", style="italic #c7c4d7"))
        return self

    def action_cursor_down(self) -> None:
        """Move the cursor down one commit in the log."""
        if self.is_detail_mode:
            return
        if self._cursor_index < len(self._log_lines) - 1:
            self._cursor_index += 1
            self._refresh_content()
            self._scroll_to_cursor()

    def action_cursor_up(self) -> None:
        """Move the cursor up one commit in the log."""
        if self.is_detail_mode:
            return
        if self._cursor_index > 0:
            self._cursor_index -= 1
            self._refresh_content()
            self._scroll_to_cursor()

    def _scroll_to_cursor(self) -> None:
        """Ensure the cursor line is visible in the viewport."""
        _ = self.scroll_to(y=self._cursor_index, animate=False)

    def _refresh_content(self) -> None:
        """Re-render either the detail view or the graph log."""
        if self._detail_text is not None:
            _ = super().clear()
            _ = self.write(self._detail_text)
            return
        text = Text()
        for i, line in enumerate(self._log_lines):
            if not line:
                text.append("\n")
                continue
            rendered = self._render_log_line(line, cursor=i == self._cursor_index)
            text.append(rendered)
            text.append("\n")
        _ = super().clear()
        _ = self.write(text)

    @staticmethod
    def _render_log_line(line: str, cursor: bool = False) -> Text:
        """Render one raw graph line with graph/ref/message coloring."""
        result = Text()

        if cursor:
            result.append(" \u276f", style="bold #9c60ec")
        else:
            result.append("  ")

        graph_part = ""
        content_part = line

        for i, ch in enumerate(line):
            if ch not in "*|/\\ -_`":
                graph_part = line[:i]
                content_part = line[i:]
                break
        else:
            result.append(line, style="#908fa0")
            return result

        for ch in graph_part:
            if ch == "*":
                result.append("*", style="bold #9c60ec")
            elif ch in "|/\\":
                result.append(ch, style="#908fa0")
            else:
                result.append(ch, style="#c7c4d7")

        content = content_part.strip()
        if not content:
            return result

        parts = content.split(" ", 1)
        # Skip the hash (parts[0]), only show the rest (message + refs)
        rest = parts[1] if len(parts) > 1 else ""

        if rest:
            rest_text = Text()
            i = 0
            while i < len(rest):
                if rest[i] == "(":
                    paren_depth = 0
                    paren_start = i
                    while i < len(rest):
                        if rest[i] == "(":
                            paren_depth += 1
                        elif rest[i] == ")":
                            paren_depth -= 1
                            if paren_depth == 0:
                                i += 1
                                break
                        i += 1
                    refs_content = rest[paren_start:i]
                    rest_text.append(refs_content, style="bold #ffb783")
                else:
                    rest_text.append(rest[i], style="#e4e1ed")
                    i += 1

            result.append(" ")
            result.append(rest_text)

        return result
