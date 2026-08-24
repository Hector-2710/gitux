"""Tests for gitux.ui.widgets.branch_screen.BranchScreen."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from textual.app import App
from textual.widgets import OptionList, Static

from gitux.git import GitError
from gitux.ui.widgets import BranchScreen


def _make_screen():
    presenter = Mock()
    return BranchScreen(presenter), presenter


def _selection_event(prompt: str):
    return SimpleNamespace(option=SimpleNamespace(prompt=prompt))


class TestSelectionHandler:
    def test_selection_switches_and_dismisses(self) -> None:
        screen, presenter = _make_screen()
        with patch.object(screen, "dismiss") as mock_dismiss, patch.object(screen, "notify") as mock_notify:
            screen.on_option_list_option_selected(_selection_event("feature/x"))
        presenter.switch_branch.assert_called_once_with("feature/x")
        mock_dismiss.assert_called_once_with("feature/x")
        mock_notify.assert_not_called()

    def test_selection_git_error_notifies_and_stays_open(self) -> None:
        screen, presenter = _make_screen()
        presenter.switch_branch.side_effect = GitError("dirty working tree")
        with patch.object(screen, "dismiss") as mock_dismiss, patch.object(screen, "notify") as mock_notify:
            screen.on_option_list_option_selected(_selection_event("feature/x"))
        mock_notify.assert_called_once_with("dirty working tree", severity="error")
        mock_dismiss.assert_not_called()

    def test_cancel_dismisses_none(self) -> None:
        screen, _ = _make_screen()
        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.action_cancel()
        mock_dismiss.assert_called_once_with(None)


class BranchApp(App):
    def __init__(self, branches: list[str]) -> None:
        super().__init__()
        self._presenter = Mock()
        self._presenter.get_branches.return_value = branches

    def on_mount(self) -> None:
        self.push_screen(BranchScreen(self._presenter))


class TestMountedFlow:
    @pytest.mark.asyncio
    async def test_populates_options_and_focuses_list(self) -> None:
        app = BranchApp(["feature/x", "main"])
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.screen.__class__.__name__ == "BranchScreen"
            option_list = app.screen.query_one("#branch-option-list", OptionList)
            assert option_list.option_count == 2
            assert option_list.has_focus
            hint = app.screen.query_one("#branch-modal-hint", Static)
            assert hint.content != "No branches found"

    @pytest.mark.asyncio
    async def test_empty_list_shows_hint_and_escape_cancels(self) -> None:
        app = BranchApp([])
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.screen.__class__.__name__ == "BranchScreen"
            hint = app.screen.query_one("#branch-modal-hint", Static)
            assert hint.content == "No branches found"
            await pilot.press("escape")
            assert app.screen.__class__.__name__ != "BranchScreen"
