"""Tests for gitux.ui.widgets.diff_viewer.DiffViewerWidget.

Regression coverage for the "diff viewer scrolls to end on file switch" bug:
the widget must always display newly shown diffs from the top.
"""

import pytest
from textual.app import App, ComposeResult

from gitux.ui.widgets.diff_viewer import (
    DiffViewerWidget,
    _MAX_DIFF_LINES,
    _format_gutter,
)


def _diff_long(line_count: int = 120) -> str:
    """Build a unified diff long enough to overflow a 40-row viewport."""
    lines = ["diff --git a/app.py b/app.py", "index 0000000..1111111"]
    lines.append(f"@@ -1,{line_count} +1,{line_count} @@")
    lines.extend(f" context line {i}" for i in range(line_count))
    return "\n".join(lines)


def _diff_with_changes() -> str:
    """A small diff exercising context, addition, and deletion lines."""
    return "\n".join(
        [
            "diff --git a/f.txt b/f.txt",
            "index abc1234..def5678 100644",
            "--- a/f.txt",
            "+++ b/f.txt",
            "@@ -1,3 +1,4 @@",
            " line1",
            "-old",
            "+new1",
            "+new2",
            " line3",
        ]
    )


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


def _rendered_lines(viewer: DiffViewerWidget) -> list[str]:
    """Return the plain text of every rendered line in the viewer."""
    return [strip.text for strip in viewer.lines if strip.text]


def _line_style(viewer: DiffViewerWidget, index: int):
    """Return the style of the first segment of a rendered line."""
    return next(iter(viewer.lines[index])).style


@pytest.mark.asyncio
async def test_file_header_lines_are_hidden():
    """FR-02: ---/+++ file-header lines are hidden, not rendered as changes."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_with_changes())
        await pilot.pause()
        rendered = _rendered_lines(viewer)
        assert not any("--- a/f.txt" in line for line in rendered)
        assert not any("+++ b/f.txt" in line for line in rendered)
        # The hunk header is the first rendered line.
        assert rendered[0] == "  @@ -1,3 +1,4 @@"


@pytest.mark.asyncio
async def test_no_newline_marker_does_not_advance_counters():
    """FR-03: \\ No newline at end of file is a special line, no counter advance."""
    diff = "\n".join(
        [
            "diff --git a/f.txt b/f.txt",
            "index abc1234..def5678 100644",
            "--- a/f.txt",
            "+++ b/f.txt",
            "@@ -1,3 +1,3 @@",
            " line1",
            "-old",
            "+new",
            " line3",
            "\\ No newline at end of file",
        ]
    )
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(diff)
        await pilot.pause()
        rendered = _rendered_lines(viewer)
        # The marker is rendered as a special line without a gutter.
        assert rendered[-1] == "  \\ No newline at end of file"
        # The context line before the marker keeps its correct line number.
        assert rendered[-2] == "    3 │  line3"


@pytest.mark.asyncio
async def test_gutter_context():
    """FR-04: context lines show the new line number."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_with_changes())
        await pilot.pause()
        rendered = _rendered_lines(viewer)
        assert rendered[1] == "    1 │  line1"
        # After the change, the context line shows the new line number.
        assert rendered[-1] == "    4 │  line3"


@pytest.mark.asyncio
async def test_gutter_added():
    """FR-05: added lines show the new line number."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_with_changes())
        await pilot.pause()
        rendered = _rendered_lines(viewer)
        assert rendered[3] == "    2 │ +new1"
        assert rendered[4] == "    3 │ +new2"


@pytest.mark.asyncio
async def test_gutter_deleted():
    """FR-06: deleted lines show the old line number."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_with_changes())
        await pilot.pause()
        rendered = _rendered_lines(viewer)
        assert rendered[2] == "    2 │ -old"


@pytest.mark.asyncio
async def test_added_line_has_green_background():
    """FR-07: added lines have green background + green text."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_with_changes())
        await pilot.pause()
        style = _line_style(viewer, 3)  # first added line
        assert style.bgcolor is not None
        assert style.bgcolor.triplet.hex == "#123a2a"
        assert style.color.triplet.hex == "#10b981"


@pytest.mark.asyncio
async def test_deleted_line_has_red_background():
    """FR-08: deleted lines have red background + red text."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_with_changes())
        await pilot.pause()
        style = _line_style(viewer, 2)  # deleted line
        assert style.bgcolor is not None
        assert style.bgcolor.triplet.hex == "#3a1d1d"
        assert style.color.triplet.hex == "#ffb4ab"


@pytest.mark.asyncio
async def test_context_line_has_no_background():
    """FR-09: context lines have default color, no background."""
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_with_changes())
        await pilot.pause()
        style = _line_style(viewer, 1)  # first context line
        assert style.bgcolor is None
        assert style.color.triplet.hex == "#e4e1ed"


@pytest.mark.asyncio
async def test_truncation_notice_uses_2000_limit():
    """FR-11/FR-12: diffs over _MAX_DIFF_LINES show a truncation notice."""
    context_lines = _MAX_DIFF_LINES + 10
    # _diff_long adds 2 metadata lines + 1 hunk header before the context.
    total = context_lines + 3
    app = _DiffApp()
    async with app.run_test(size=(100, 40)) as pilot:
        viewer = app.query_one("#diff-viewer", DiffViewerWidget)
        viewer.show_diff(_diff_long(line_count=context_lines))
        await pilot.pause()
        rendered = _rendered_lines(viewer)
        assert rendered[-1] == f"  [{_MAX_DIFF_LINES} of {total} lines shown]"


def test_format_gutter():
    """FR-04/05/06: gutter formatting for context/add/delete."""
    assert _format_gutter(123, 123) == "  123 │ "
    assert _format_gutter(None, 7) == "    7 │ "
    assert _format_gutter(7, None) == "    7 │ "
    # Context after a change shows the new line number.
    assert _format_gutter(4, 5) == "    5 │ "
