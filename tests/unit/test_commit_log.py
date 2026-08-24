"""Tests for gitux.ui.widgets.commit_log CommitLogWidget and extract_commit_hash."""

from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult

from gitux.ui.widgets.commit_log import CommitLogWidget, extract_commit_hash


class TestExtractCommitHash:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("* c4474af (HEAD -> main) feat: initial", "c4474af"),
            ("| * a1b2c3d (origin/main) chore: merged", "a1b2c3d"),
            ("* 0000000 merge branch 'x'", "0000000"),
        ],
    )
    def test_returns_hash(self, line, expected) -> None:
        assert extract_commit_hash(line) == expected

    @pytest.mark.parametrize(
        "line",
        ["|", "|\\", "", "   ", "*", "|/\\"],
    )
    def test_graph_only_lines_return_none(self, line) -> None:
        assert extract_commit_hash(line) is None


class LogApp(App):
    def compose(self) -> ComposeResult:
        self.log_widget = CommitLogWidget(id="commit-log")
        yield self.log_widget


class TestDetailMode:
    @pytest.mark.asyncio
    async def test_show_details_enters_detail_mode(self) -> None:
        app = LogApp()
        async with app.run_test():
            log = app.log_widget
            log.show_log("* c4474af (HEAD -> main) feat: initial\n|")
            with patch.object(log, "scroll_home") as mock_home:
                log.show_details("c4474af", "c4474af Jane <j@x>")
            assert log.is_detail_mode is True
            assert log._detail_hash == "c4474af"
            assert log._detail_text == "c4474af Jane <j@x>"
            mock_home.assert_called_once_with(animate=False)

    @pytest.mark.asyncio
    async def test_exit_details_restores_log(self) -> None:
        app = LogApp()
        async with app.run_test():
            log = app.log_widget
            log.show_log("* c4474af (HEAD -> main) feat: initial")
            log.show_details("c4474af", "detail text")
            with patch.object(log, "_scroll_to_cursor") as mock_scroll:
                log.exit_details()
            assert log.is_detail_mode is False
            assert log._detail_hash is None
            assert log._detail_text is None
            mock_scroll.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_show_log_resets_detail_mode(self) -> None:
        app = LogApp()
        async with app.run_test():
            log = app.log_widget
            log.show_log("* c4474af feat: initial")
            log.show_details("c4474af", "detail")
            log.show_log("* 1111111 feat: another")
            assert log.is_detail_mode is False
            assert log._detail_text is None

    @pytest.mark.asyncio
    async def test_clear_resets_detail_mode(self) -> None:
        app = LogApp()
        async with app.run_test():
            log = app.log_widget
            log.show_log("* c4474af feat: initial")
            log.show_details("c4474af", "detail")
            log.clear()
            assert log.is_detail_mode is False
            assert log._detail_text is None

    @pytest.mark.asyncio
    async def test_cursor_actions_noop_in_detail_mode(self) -> None:
        app = LogApp()
        async with app.run_test():
            log = app.log_widget
            log.show_log("* c4474af feat: initial\n| * a1b2c3d chore: x")
            log.action_cursor_down()
            index_before = log._cursor_index
            log.show_details("c4474af", "detail")
            log.action_cursor_down()
            log.action_cursor_up()
            assert log._cursor_index == index_before
            assert log.is_detail_mode is True

    @pytest.mark.asyncio
    async def test_cursor_line_empty_log_is_none(self) -> None:
        app = LogApp()
        async with app.run_test():
            log = app.log_widget
            assert log.cursor_line is None

    @pytest.mark.asyncio
    async def test_cursor_line_returns_current_line(self) -> None:
        app = LogApp()
        async with app.run_test():
            log = app.log_widget
            log.show_log("* c4474af feat: initial\n| * a1b2c3d chore: x")
            log.action_cursor_down()
            assert log.cursor_line == "| * a1b2c3d chore: x"
