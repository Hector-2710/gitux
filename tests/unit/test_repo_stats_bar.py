"""Tests for gitux.ui.widgets.repo_stats_bar.RepoStatsBar (skeleton K6).

The bar is the counts strip + sync + step dots — the old subject/time line
is gone (scope S6, amended).
"""

import pytest
from textual.app import App

from gitux.domain import FileCounts, RemoteStatus
from gitux.ui.widgets import RepoStatsBar


class BarApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.bar = RepoStatsBar()

    def compose(self):
        yield self.bar


def _counts(staged=0, modified=0, untracked=0) -> FileCounts:
    return FileCounts(staged=staged, modified=modified, untracked=untracked, conflicts=0)


@pytest.mark.asyncio
async def test_counts_strip_renders_all_three_sections():
    app = BarApp()
    async with app.run_test():
        app.bar.update_stats(
            counts=_counts(staged=3, modified=2, untracked=1),
            staged_stat=(142, 28),
            remote_status=None,
            steps=1,
        )
        left = str(app.bar.query_one("#stats-left").content)
        assert "STAGED (3, +142 -28)" in left
        assert "UNSTAGED (2)" in left
        assert "UNTRACKED (1)" in left


@pytest.mark.asyncio
async def test_counts_strip_omits_diffstat_when_empty():
    app = BarApp()
    async with app.run_test():
        app.bar.update_stats(
            counts=_counts(staged=2),
            staged_stat=(0, 0),
            remote_status=None,
            steps=0,
        )
        left = str(app.bar.query_one("#stats-left").content)
        assert "STAGED (2)" in left
        assert "+" not in left.split("│")[0]  # no diffstat segment


@pytest.mark.asyncio
async def test_sync_green_when_clean():
    app = BarApp()
    async with app.run_test():
        app.bar.update_stats(
            counts=_counts(),
            staged_stat=(0, 0),
            remote_status=RemoteStatus("origin", "main", 0, 0),
            steps=0,
        )
        sync = app.bar.query_one("#stats-sync")
        assert "\u21910 \u21930" in str(sync.content)


@pytest.mark.asyncio
async def test_sync_amber_when_ahead():
    app = BarApp()
    async with app.run_test():
        app.bar.update_stats(
            counts=_counts(),
            staged_stat=(0, 0),
            remote_status=RemoteStatus("origin", "main", 2, 0),
            steps=2,
        )
        sync = app.bar.query_one("#stats-sync")
        assert "\u21912 \u21930" in str(sync.content)


@pytest.mark.asyncio
async def test_sync_red_when_behind():
    app = BarApp()
    async with app.run_test():
        app.bar.update_stats(
            counts=_counts(),
            staged_stat=(0, 0),
            remote_status=RemoteStatus("origin", "main", 0, 2),
            steps=3,
        )
        sync = app.bar.query_one("#stats-sync")
        assert "\u21910 \u21932" in str(sync.content)


@pytest.mark.asyncio
async def test_sync_empty_without_remote():
    app = BarApp()
    async with app.run_test():
        app.bar.update_stats(
            counts=_counts(),
            staged_stat=(0, 0),
            remote_status=RemoteStatus("", "", 0, 0),
            steps=0,
        )
        sync = app.bar.query_one("#stats-sync")
        assert str(sync.content) == ""


@pytest.mark.asyncio
async def test_step_dots_render_lit_count():
    app = BarApp()
    async with app.run_test():
        app.bar.update_stats(
            counts=_counts(staged=1),
            staged_stat=(0, 0),
            remote_status=None,
            steps=1,
        )
        steps = str(app.bar.query_one("#stats-steps").content)
        assert steps.count("\u25cf") == 1
        assert steps.count("\u25cb") == 2
