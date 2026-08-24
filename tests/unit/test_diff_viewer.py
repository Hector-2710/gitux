"""Tests for gitux.ui.widgets.diff_viewer.DiffViewerWidget.

Regression coverage for the "diff viewer scrolls to end on file switch" bug:
the widget must always display newly shown diffs from the top.
"""

import pytest
from textual.app import App, ComposeResult

from gitux.ui.widgets.diff_viewer import DiffViewerWidget


def _diff_long(line_count: int = 120) -> str:
    """Build a unified diff long enough to overflow a 40-row viewport."""
    lines = ["diff --git a/app.py b/app.py", "index 0000000..1111111"]
    lines.append(f"@@ -1,{line_count} +1,{line_count} @@")
    lines.extend(f" context line {i}" for i in range(line_count))
    return "\n".join(lines)


class _DiffApp(App):
    """Minimal app hosting a DiffViewerWidget for behavioural tests."""

    def compose(self) -> ComposeResult:
        yield DiffViewerWidget(id="diff-viewer")


@pytest.fixture
def diff_app():
    """Create a mounted diff viewer with a known size."""
    return _DiffApp()


@pytest.mark.asyncio
async def test_auto_scroll_disabled_at_init():
    """AC-1: the RichLog backing the viewer is built without auto-scroll."""
    app = _DiffApp()
    async with app.run_test() as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        assert viewer.auto_scroll is False


@pytest.mark.asyncio
async def test_show_diff_starts_at_top():
    """AC-2: a long diff is displayed from the top, not the end."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_long())
        await pilot.pause()
        assert viewer.scroll_y == 0


@pytest.mark.asyncio
async def test_show_diff_resets_previous_scroll():
    """AC-3: showing a new diff after scrolling resets the view to the top."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_long())
        await pilot.pause()
        viewer.scroll_to(y=1000, animate=False)
        await pilot.pause()
        assert viewer.scroll_y > 0  # sanity: the view was actually scrolled
        viewer.show_diff(_diff_long())
        await pilot.pause()
        assert viewer.scroll_y == 0


@pytest.mark.asyncio
async def test_placeholder_shows_at_top():
    """AC-3: clearing after scrolling returns the view to the top."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_long())
        await pilot.pause()
        viewer.scroll_to(y=1000, animate=False)
        await pilot.pause()
        viewer.clear()
        await pilot.pause()
        assert viewer.scroll_y == 0
