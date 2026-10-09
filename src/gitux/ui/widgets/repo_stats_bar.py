"""Repo stats bar — counts strip + sync + step dots (skeleton K6).

Line 1: ``STAGED (n, +x -y) │ UNSTAGED (n) │ UNTRACKED (n)``
Line 2: sync (``↑ahead ↓behind``, left) + the commit-step dots (right).

Replaces the old subject/time line (scope S6, amended) and absorbs the
footer's sync indicator (K7 — the footer is gone). Colors per surface V1/V4:
staged = cyan (info), unstaged = amber (pending), untracked = dim;
sync is green when clean, amber when ahead, red when behind.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gitux.domain import FileCounts, RemoteStatus
from gitux.ui import tokens


class RepoStatsBar(Vertical):
    """Two-line status bar fed by ``GituxApp._refresh_all``."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._counts = FileCounts(staged=0, modified=0, untracked=0, conflicts=0)
        self._staged_stat: tuple[int, int] = (0, 0)
        self._remote: RemoteStatus | None = None
        self._steps = 0

    def compose(self) -> ComposeResult:
        """Yield the counts line and the sync+dots line."""
        yield Static("", id="stats-left")
        with Horizontal(id="stats-second"):
            yield Static("", id="stats-sync")
            yield Static("", id="stats-steps")

    def update_stats(
        self,
        counts: FileCounts,
        staged_stat: tuple[int, int],
        remote_status: RemoteStatus | None,
        steps: int,
    ) -> None:
        """Render the bar from the current git state (K6)."""
        self._counts = counts
        self._staged_stat = staged_stat
        self._remote = remote_status
        self._steps = steps
        self._update_render()

    def _update_render(self) -> None:
        """Push the counts, sync, and dots to the child widgets."""
        if not self.is_mounted:
            return
        self.query_one("#stats-left", Static).update(self._render_counts())
        self.query_one("#stats-sync", Static).update(self._render_sync())
        self.query_one("#stats-steps", Static).update(self._render_steps())

    # ── Line 1: the counts strip ────────────────────────────────────────

    def _render_counts(self) -> Text:
        """``STAGED (n, +x -y) │ UNSTAGED (n) │ UNTRACKED (n)``."""
        adds, dels = self._staged_stat
        text = Text(no_wrap=True)

        text.append("STAGED", style=f"bold {tokens.CYAN}")
        staged_label = f" ({self._counts.staged}"
        if adds or dels:
            staged_label += f", +{adds} -{dels}"
        staged_label += ")"
        text.append(staged_label, style=tokens.TEXT)

        text.append(" \u2502 ", style=tokens.TEXT_DIM)
        text.append("UNSTAGED", style=f"bold {tokens.AMBER}")
        text.append(f" ({self._counts.modified})", style=tokens.TEXT)

        text.append(" \u2502 ", style=tokens.TEXT_DIM)
        text.append("UNTRACKED", style=f"bold {tokens.TEXT_DIM}")
        text.append(f" ({self._counts.untracked})", style=tokens.TEXT)

        return text

    # ── Line 2: sync (left) + step dots (right) ──────────────────────────

    def _render_sync(self) -> Text:
        """``↑ahead ↓behind`` colored by urgency (V4): green clean, amber
        ahead (push pending), red behind (pull needed). Empty without remote."""
        text = Text(no_wrap=True)
        remote = self._remote
        if remote is None or not remote.remote:
            return text
        if remote.behind > 0:
            style = tokens.RED
        elif remote.ahead > 0:
            style = tokens.AMBER
        else:
            style = tokens.GREEN
        text.append(f"\u2191{remote.ahead} \u2193{remote.behind}", style=f"bold {style}")
        return text

    def _render_steps(self) -> Text:
        """The commit-step dots: staged → commit → push/pull (K5 legend)."""
        text = Text(no_wrap=True)
        for i in range(3):
            lit = i < self._steps
            text.append(
                "\u25cf" if lit else "\u25cb",
                style=(f"bold {tokens.GREEN}" if lit else tokens.TEXT_DIM),
            )
            if i < 2:
                text.append("  ", style="")
        return text
