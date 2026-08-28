"""Repo stats bar — one-line repository statistics below the top app bar."""

import time
from typing import Any, override

from rich.cells import cell_len
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from gitux.domain import FileCounts, HeadSummary

_MAX_USER_CHARS: int = 16
_MAX_REPO_CHARS: int = 32
_MAX_REMOTE_CHARS: int = 32
_MAX_HEAD_SUBJECT_CHARS: int = 40
_DEFAULT_RENDER_WIDTH: int = 200  # unmounted fallback so bare _render_text() is full
_PADDING_COLS: int = 2  # matches `padding: 0 1` on #stats-bar

# drop priority, LOWEST first (head is never dropped)
_SEGMENT_PRIORITY: tuple[str, ...] = ("ahead_behind", "remote", "repo", "user", "files", "date", "head")

_PREFIX_CELLS: int = 2  # " ■"
_STEPS_CELLS: int = 7  # "● ● ● ●"
_SEPARATOR_CELLS: int = 3  # " │ "


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


class RepoStatsBar(Horizontal):
    """Single-line stats bar fed by ``GituxApp._refresh_all``.

    Left side renders `` ■ │ user │ hash subject │ date │ +s ~m ?u [!c] │ ↑a ↓b │ remote``;
    the commit-step indicator ``● ● ● ●`` is pinned to the right edge.
    Uses hybrid B3 truncation: hard caps + width-adaptive segment drop.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._user: str = ""
        self._head_summary: HeadSummary | None = None
        self._file_counts: FileCounts | None = None
        self._ahead = 0
        self._behind = 0
        self._remote = "(local)"
        self._remote_branch = ""
        self._repo_name: str = ""
        self._steps: int = 0

    @override
    def compose(self) -> ComposeResult:
        """Yield the left stats text and the right-aligned step indicator."""
        yield Static("", id="stats-left")
        yield Static("", id="stats-steps")

    def update_stats(
        self,
        user: str = "",
        head_summary: HeadSummary | None = None,
        file_counts: FileCounts | None = None,
        ahead: int = 0,
        behind: int = 0,
        remote: str = "(local)",
        remote_branch: str = "",
        repo_name: str = "",
        steps: int | None = None,
    ) -> None:
        """Render the stats bar with the given repo state (safe defaults included).

        ``steps`` optionally overrides the derived step mask (test hook; the App
        never passes it).
        """
        self._remote = remote or "(local)"
        self._remote_branch = remote_branch if remote else ""
        self._user = user
        self._head_summary = head_summary
        self._file_counts = file_counts
        self._ahead = ahead
        self._behind = behind
        self._repo_name = repo_name
        if steps is None:
            has_remote = bool(self._remote) and self._remote != "(local)"
            step1 = (self._file_counts or FileCounts(0, 0, 0, 0)).staged > 0
            step2 = self._head_summary is not None
            step3 = has_remote and self._ahead == 0
            step4 = has_remote and self._ahead == 0 and self._behind == 0
            self._steps = (
                (1 if step1 else 0)
                + (1 if (step1 and step2) else 0)
                + (1 if (step1 and step2 and step3) else 0)
                + (1 if (step1 and step2 and step3 and step4) else 0)
            )
        else:
            self._steps = steps
        self._update_render()

    def _update_render(self) -> None:
        """Push the current stats text and step indicator to the child widgets."""
        if not self.is_mounted:
            return
        self.query_one("#stats-left", Static).update(self._render_text())
        self.query_one("#stats-steps", Static).update(self._render_steps())

    def _build_segments(self) -> list[dict[str, Any]]:
        """Build segments in locked visual order with text, style, and drop info."""
        segments: list[dict[str, Any]] = []

        if self._repo_name:
            segments.append({
                "name": "repo",
                "plain": self._repo_name[:_MAX_REPO_CHARS],
                "style": "bold #e4e1ed",
            })

        segments.append({
            "name": "user",
            "plain": (self._user or "unknown")[:_MAX_USER_CHARS],
            "style": "#e4e1ed",
        })

        summary = self._head_summary
        if summary is None:
            segments.append({
                "name": "head",
                "plain": "(no commits)",
                "hash": "",
                "subject": "(no commits)",
                "style": "#e4e1ed",
            })
        else:
            subject = summary.subject
            if len(subject) > _MAX_HEAD_SUBJECT_CHARS:
                subject = subject[: _MAX_HEAD_SUBJECT_CHARS - 1] + "\u2026"
            segments.append({
                "name": "head",
                "plain": subject,
                "hash": "",
                "subject": subject,
                "style": "#e4e1ed",
            })

        if summary is not None:
            segments.append({
                "name": "date",
                "plain": _format_relative_time(summary.epoch),
                "style": "#c7c4d7",
            })

        counts = self._file_counts or FileCounts(0, 0, 0, 0)
        files = f"+{counts.staged} ~{counts.modified} ?{counts.untracked}"
        if counts.conflicts > 0:
            files += f" !{counts.conflicts}"
        segments.append({
            "name": "files",
            "plain": files,
            "style": "#c7c4d7",
        })

        segments.append({
            "name": "ahead_behind",
            "plain": f"\u2191{self._ahead} \u2193{self._behind}",
            "style": "bold #c0c1ff",
        })

        remote_slug = (
            f"{self._remote}/{self._remote_branch}" if self._remote_branch else self._remote
        )
        segments.append({
            "name": "remote",
            "plain": remote_slug[:_MAX_REMOTE_CHARS],
            "style": "#e4e1ed",
        })

        return segments

    def _total_cells(self, segments: list[dict[str, Any]]) -> int:
        """Total rendered cell width of all segments plus prefix and separators."""
        return (
            _PREFIX_CELLS
            + sum(cell_len(seg["plain"]) for seg in segments)
            + _SEPARATOR_CELLS * (len(segments) - 1)
        )

    def _fit_segments(self, segments: list[dict[str, Any]], width: int) -> list[dict[str, Any]]:
        """Drop lowest-priority segments, then elide the head subject to fit width.

        ``width`` is the available width for the left text (segments + prefix +
        separators), i.e. the total bar width minus the step-indicator width.
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
            hash_len = cell_len(head["hash"])
            avail = width - _PREFIX_CELLS - hash_len - 1
            if avail < 1:
                if head["hash"]:
                    head["plain"] = head["hash"]
                else:
                    head["plain"] = head["plain"][: max(0, width - _PREFIX_CELLS)]
            else:
                elided = head["subject"][: avail - 1] + "\u2026"
                head["plain"] = (
                    f"{head['hash']} {elided}" if head["hash"] else elided
                )
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
        text.append(" \u25a0", style="bold #c0c1ff")
        for seg in segments:
            text.append(" \u2502 ", style="#c7c4d7")
            text.append(seg["plain"], style=seg["style"])
        return text

    def _render_steps(self) -> Text:
        """Render the commit-step indicator dots (pinned to the right edge)."""
        text = Text(no_wrap=True)
        for i in range(4):
            lit = i < self._steps
            text.append(
                "\u25cf" if lit else "\u25cb",
                style=("bold #34d399" if lit else "#908fa0"),
            )
            if i < 3:
                text.append(" ", style="")
        return text
