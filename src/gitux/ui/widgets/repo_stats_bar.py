"""Repo stats bar — two-line repository status below the top app bar.

Left side shows ``repo │ hash subject │ relative time │ branch``; the four
commit-step indicator dots are rendered large on the right edge. The bar uses
rounded borders to match the rest of the UI.
"""

import time
from typing import override

from rich.cells import cell_len
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from gitux.domain import HeadSummary

_MAX_REPO_CHARS: int = 32
_MAX_BRANCH_CHARS: int = 24
_MAX_HEAD_SUBJECT_CHARS: int = 40
_DEFAULT_RENDER_WIDTH: int = 200  # unmounted fallback so bare _render_text() is full
_PADDING_COLS: int = 2  # matches `padding: 0 1` on #stats-bar

# drop priority, LOWEST first (head is never dropped)
_SEGMENT_PRIORITY: tuple[str, ...] = ("branch", "repo", "date", "head")

_PREFIX_CELLS: int = 0  # no leading icon anymore
_SEPARATOR_CELLS: int = 3  # " │ "
_STEPS_CELLS: int = 10  # "●  ●  ●  ●" (4 dots + 3 double-space gaps)


def _format_relative_time(epoch: int, *, now: float | None = None) -> str:
    """Format an epoch seconds as a relative English string (floor division)."""
    now = time.time() if now is None else now
    delta = max(0, int(now - epoch))
    if delta < 60:
        return "just now"
    if delta < 90:
        return "1 minute ago"
    if delta < 2700:
        return f"{delta // 60} minutes ago"
    if delta < 5400:
        return "1 hour ago"
    if delta < 86400:
        return f"{delta // 3600} hours ago"
    if delta < 129600:
        return "1 day ago"
    if delta < 604800:
        return f"{delta // 86400} days ago"
    if delta < 2592000:
        return f"{delta // 604800} weeks ago"
    if delta < 31536000:
        return f"{delta // 2592000} months ago"
    return f"{delta // 31536000} years ago"


class RepoStatsBar(Vertical):
    """Two-line status bar fed by ``GituxApp._refresh_all``.

    Line 1 renders ``repo │ hash subject │ relative time │ branch``; line 2
    renders the commit-step indicator ``● ● ● ●`` large on the right edge.
    Uses hybrid B3 truncation: hard caps + width-adaptive segment drop.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._repo_name: str = ""
        self._branch: str = ""
        self._head_summary: HeadSummary | None = None
        self._steps: int = 0

    @override
    def compose(self) -> ComposeResult:
        """Yield the left stats text and the right-aligned step indicator."""
        yield Static("", id="stats-left")
        yield Static("", id="stats-steps")

    def update_stats(
        self,
        repo_name: str = "",
        branch: str = "",
        head_summary: HeadSummary | None = None,
        steps: int | None = None,
    ) -> None:
        """Render the stats bar with the given repo state (safe defaults included).

        ``steps`` optionally overrides the derived step mask (test hook; the App
        never passes it).
        """
        self._repo_name = repo_name
        self._branch = branch
        self._head_summary = head_summary
        if steps is None:
            self._steps = 0
        else:
            self._steps = steps
        self._update_render()

    def _update_render(self) -> None:
        """Push the current stats text and step indicator to the child widgets."""
        if not self.is_mounted:
            return
        self.query_one("#stats-left", Static).update(self._render_text())
        self.query_one("#stats-steps", Static).update(self._render_steps())

    def _build_segments(self) -> list[dict[str, str]]:
        """Build segments in locked visual order with text and style."""
        segments: list[dict[str, str]] = []

        if self._repo_name:
            segments.append({
                "name": "repo",
                "plain": self._repo_name[:_MAX_REPO_CHARS],
                "style": "bold #e4e1ed",
            })

        summary = self._head_summary
        if summary is None:
            segments.append({
                "name": "head",
                "plain": "(no commits)",
                "subject": "(no commits)",
                "style": "#e4e1ed",
            })
        else:
            subject = summary.subject
            if len(subject) > _MAX_HEAD_SUBJECT_CHARS:
                subject = subject[: _MAX_HEAD_SUBJECT_CHARS - 1] + "\u2026"
            segments.append({
                "name": "head",
                "plain": f"{summary.short_hash} {subject}",
                "subject": subject,
                "style": "#e4e1ed",
            })

        if summary is not None:
            segments.append({
                "name": "date",
                "plain": _format_relative_time(summary.epoch),
                "style": "#c7c4d7",
            })

        if self._branch:
            segments.append({
                "name": "branch",
                "plain": self._branch[:_MAX_BRANCH_CHARS],
                "style": "bold #c0c1ff",
            })

        return segments

    def _total_cells(self, segments: list[dict[str, str]]) -> int:
        """Total rendered cell width of all segments plus separators."""
        return (
            _PREFIX_CELLS
            + sum(cell_len(seg["plain"]) for seg in segments)
            + _SEPARATOR_CELLS * (len(segments) - 1)
        )

    def _fit_segments(self, segments: list[dict[str, str]], width: int) -> list[dict[str, str]]:
        """Drop lowest-priority segments, then elide the head subject to fit width.

        ``width`` is the available width for the left text (segments + separators),
        i.e. the total bar width minus the step-indicator width.
        """
        total = self._total_cells(segments)
        while total > width and len(segments) > 1:
            droppable = [seg for seg in segments if seg["name"] != "head"]
            if not droppable:
                break
            to_drop = min(droppable, key=lambda seg: _SEGMENT_PRIORITY.index(seg["name"]))
            segments.remove(to_drop)
            total = self._total_cells(segments)

        if len(segments) == 1 and total > width:
            head = segments[0]
            avail = width - _PREFIX_CELLS - 1
            if avail < 1:
                head["plain"] = head["plain"][: max(0, width - _PREFIX_CELLS)]
            else:
                elided = head["subject"][: avail - 1] + "\u2026"
                head["plain"] = elided
        return segments

    def _render_text(self, width: int | None = None) -> Text:
        """Render the left stats line, dropping segments to fit the given width."""
        if width is None:
            width = self.size.width - _PADDING_COLS if self.is_mounted else 0
        if width <= 0:
            width = _DEFAULT_RENDER_WIDTH
        segments = self._build_segments()
        segments = self._fit_segments(segments, width - _STEPS_CELLS)

        text = Text(no_wrap=True)
        for i, seg in enumerate(segments):
            if i > 0:
                text.append(" \u2502 ", style="#c7c4d7")
            text.append(seg["plain"], style=seg["style"])
        return text

    def _render_steps(self) -> Text:
        """Render the commit-step indicator dots (pinned to the right edge).

        Dots are spaced wider and rendered bold to read larger against the
        two-line status bar.
        """
        text = Text(no_wrap=True)
        for i in range(4):
            lit = i < self._steps
            text.append(
                "\u25cf" if lit else "\u25cb",
                style=("bold #34d399" if lit else "#908fa0"),
            )
            if i < 3:
                text.append("  ", style="")
        return text
