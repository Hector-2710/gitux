import unittest.mock

import pytest

from gitux.ui.app import GituxApp
from gitux.ui.widgets.commit_log_screen import CommitLogScreen

_GRAPH_LOG = "* c4474af feat: initial\n|"
_DETAIL_TEXT = "\n".join(f"detail line {i:02d}" for i in range(60))


async def _open_log(app, pilot, log=_GRAPH_LOG) -> CommitLogScreen:
    """Open the commit-log modal with a mocked log and clean refresh state."""
    with unittest.mock.patch.object(app.repo, "get_commit_log", return_value=log), \
        unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status", return_value=[]
        ):
        await pilot.press("l")
    return app.screen


@pytest.mark.asyncio
async def test_commit_log_modal_opens_on_l():
    app = GituxApp()
    async with app.run_test() as pilot:
        screen = await _open_log(app, pilot)
        assert isinstance(screen, CommitLogScreen)
        assert screen.query_one("#commit-log-modal") is not None
        assert screen.query_one("#commit-log") is not None
        assert screen.presenter is app.repo
        assert any(
            b.key == "l" and b.action == "open_commit_log"
            for b in GituxApp.BINDINGS
        )


@pytest.mark.asyncio
async def test_commit_log_modal_fetches_fresh_log_on_mount():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(
            app.repo, "get_commit_log", return_value=_GRAPH_LOG
        ) as mock_log:
            await pilot.press("l")
        mock_log.assert_called_once_with(30)
        log_widget = app.screen.query_one("#commit-log")
        assert log_widget._log_lines == _GRAPH_LOG.splitlines()


@pytest.mark.asyncio
async def test_commit_log_modal_escape_dismisses():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_commit_log", return_value=_GRAPH_LOG), \
            unittest.mock.patch(
                "gitux.presenter.commit_presenter.get_status", return_value=[]
            ) as mock_status:
            await pilot.press("l")
            assert app.screen.__class__.__name__ == "CommitLogScreen"
            await pilot.press("escape")
        assert app.screen.__class__.__name__ != "CommitLogScreen"
        assert app.query_one("#changed-files") is not None
        assert mock_status.call_count == 0


@pytest.mark.asyncio
async def test_commit_log_modal_detail_escape_semantics():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_commit_log", return_value=_GRAPH_LOG), \
            unittest.mock.patch.object(
                app.repo, "get_commit_details", return_value=_DETAIL_TEXT
            ):
            await pilot.press("l")
            log_widget = app.screen.query_one("#commit-log")
            await pilot.press("enter")
            assert log_widget.is_detail_mode is True
            assert log_widget._detail_text == _DETAIL_TEXT
            await pilot.press("escape")
            assert log_widget.is_detail_mode is False
            assert app.screen.__class__.__name__ == "CommitLogScreen"
            await pilot.press("escape")
            assert app.screen.__class__.__name__ != "CommitLogScreen"


@pytest.mark.asyncio
async def test_commit_log_modal_no_detail_on_graph_line():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_commit_log", return_value=_GRAPH_LOG), \
            unittest.mock.patch.object(
                app.repo, "get_commit_details", return_value=_DETAIL_TEXT
            ) as mock_details:
            await pilot.press("l")
            log_widget = app.screen.query_one("#commit-log")
            await pilot.press("down")
            assert log_widget.cursor_line == "|"
            await pilot.press("enter")
            mock_details.assert_not_called()
            assert log_widget.is_detail_mode is False


@pytest.mark.asyncio
async def test_commit_log_modal_empty_log_shows_no_commits():
    app = GituxApp()
    async with app.run_test() as pilot:
        await _open_log(app, pilot, log="")
        log_widget = app.screen.query_one("#commit-log")
        assert log_widget._log_lines == []
        rendered = "".join(line.text for line in log_widget.lines)
        assert "No commits yet" in rendered


@pytest.mark.asyncio
async def test_commit_log_modal_empty_details_noop():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_commit_log", return_value=_GRAPH_LOG), \
            unittest.mock.patch.object(app.repo, "get_commit_details", return_value=""):
            await pilot.press("l")
            log_widget = app.screen.query_one("#commit-log")
            with unittest.mock.patch.object(app, "notify") as mock_notify:
                await pilot.press("enter")
            assert log_widget.is_detail_mode is False
            mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_commit_log_modal_enter_twice_opens_detail_once():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_commit_log", return_value=_GRAPH_LOG), \
            unittest.mock.patch.object(
                app.repo, "get_commit_details", return_value=_DETAIL_TEXT
            ) as mock_details:
            await pilot.press("l")
            log_widget = app.screen.query_one("#commit-log")
            await pilot.press("enter")
            await pilot.press("enter")
            assert log_widget.is_detail_mode is True
            mock_details.assert_called_once_with("c4474af")


@pytest.mark.asyncio
async def test_commit_log_modal_detail_down_scrolls_without_cursor_move():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_commit_log", return_value=_GRAPH_LOG), \
            unittest.mock.patch.object(
                app.repo, "get_commit_details", return_value=_DETAIL_TEXT
            ):
            await pilot.press("l")
            log_widget = app.screen.query_one("#commit-log")
            await pilot.press("enter")
            assert log_widget.is_detail_mode is True
            cursor_before = log_widget._cursor_index
            await pilot.press("down")
            assert log_widget._cursor_index == cursor_before
            assert log_widget.scroll_y > 0


@pytest.mark.asyncio
async def test_commit_log_modal_no_scrollbar_and_log_scrolls():
    app = GituxApp()
    async with app.run_test() as pilot:
        long_log = "\n".join(f"* {i:07x} message {i}" for i in range(80))
        await _open_log(app, pilot, log=long_log)
        log_widget = app.screen.query_one("#commit-log")
        assert log_widget.styles.scrollbar_visibility == "hidden"
        for _ in range(40):
            await pilot.press("down")
        assert log_widget.scroll_y > 0


@pytest.mark.asyncio
async def test_commit_log_modal_css():
    app = GituxApp()
    async with app.run_test() as pilot:
        await _open_log(app, pilot)
        modal = app.screen.query_one("#commit-log-modal")
        assert modal.styles.width.value == 70.0
        assert modal.styles.max_width.value == 90.0
        assert modal.styles.height.value == 80.0
        assert modal.styles.max_height.value == 85.0
        assert app.screen.styles.align == ("center", "middle")
        background = app.screen.styles.background
        assert background.rgb == (0x18, 0x16, 0x22)
        assert background.a == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_commit_log_modal_does_not_move_panels():
    app = GituxApp()
    async with app.run_test() as pilot:
        await _open_log(app, pilot)
        changed_files = app.query_one("#changed-files")
        assert app._active_block == "files"
        assert app._block_index == 0
        assert changed_files._cursor_index == 0
        with unittest.mock.patch.object(
            app.repo, "get_commit_details", return_value=_DETAIL_TEXT
        ):
            await pilot.press("enter")
            await pilot.press("down")
            await pilot.press("escape")
        assert app._active_block == "files"
        assert app._block_index == 0
        assert changed_files._cursor_index == 0
        assert app.screen.__class__.__name__ == "CommitLogScreen"