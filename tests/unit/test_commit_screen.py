"""Tests for gitux.ui.widgets.commit_screen.CommitScreen."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from textual.app import App
from textual.widgets import Input

from gitux.domain import CommitResult
from gitux.ui.widgets.commit_screen import CommitScreen


class CommitApp(App):
    def __init__(self, commit_result: CommitResult | None = None) -> None:
        super().__init__()
        self.presenter = Mock()
        self.presenter.commit.return_value = commit_result or CommitResult(
            success=True, commit_hash="abc1234"
        )

    def on_mount(self) -> None:
        self.push_screen(CommitScreen(self.presenter))


class TestMounted:
    @pytest.mark.asyncio
    async def test_input_focused_on_mount(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert screen.query_one("#commit-modal-input", Input).has_focus

    @pytest.mark.asyncio
    async def test_input_submitted_commits_raw_message(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.query_one("#commit-modal-input", Input).value = "hello"
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.on_input_submitted(SimpleNamespace())
            app.presenter.commit.assert_called_once_with("hello")
            mock_dismiss.assert_called_once_with("abc1234")

    @pytest.mark.asyncio
    async def test_empty_message_notifies_and_stays_open(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            with patch.object(screen, "notify") as mock_notify, \
                patch.object(screen, "dismiss") as mock_dismiss:
                for value in ("", "   "):
                    screen.query_one("#commit-modal-input", Input).value = value
                    screen._do_commit()
            assert mock_notify.call_count == 2
            mock_notify.assert_called_with(
                "Commit message cannot be empty", severity="error"
            )
            app.presenter.commit.assert_not_called()
            mock_dismiss.assert_not_called()

    @pytest.mark.asyncio
    async def test_commit_failure_notifies_and_stays_open(self) -> None:
        app = CommitApp(
            commit_result=CommitResult(
                success=False, error="No staged changes to commit"
            )
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.query_one("#commit-modal-input", Input).value = "hello"
            with patch.object(screen, "notify") as mock_notify, \
                patch.object(screen, "dismiss") as mock_dismiss:
                screen._do_commit()
            app.presenter.commit.assert_called_once_with("hello")
            mock_notify.assert_called_once_with(
                "No staged changes to commit", severity="error"
            )
            mock_dismiss.assert_not_called()

    @pytest.mark.asyncio
    async def test_enter_fires_once_from_input(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.query_one("#commit-modal-input", Input).value = "hello"
            await pilot.press("enter")
            app.presenter.commit.assert_called_once_with("hello")

    @pytest.mark.asyncio
    async def test_escape_cancels_without_commit(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            assert app.screen.__class__.__name__ != "CommitScreen"
            app.presenter.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_modal_children_fit_at_80x24(self) -> None:
        app = CommitApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            screen = app.screen
            modal = screen.query_one("#commit-modal")
            for child_id in (
                "#commit-modal-title",
                "#commit-modal-input",
            ):
                child = screen.query_one(child_id)
                assert child.region.height >= 1
                assert modal.region.contains_region(child.region)
