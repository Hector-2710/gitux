"""Tests for gitux.ui.widgets.branch_screen.BranchScreen (skeleton K3).

The screen is an action model: Enter switch · m merge · d delete (with
confirmation) · n new. Errors route to the app's error line (K2/T3).
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from textual.app import App
from textual.widgets import Input, OptionList, Static

from gitux.git import GitError
from gitux.ui.widgets import BranchScreen


def _make_screen():
    presenter = Mock()
    presenter.get_current_branch.return_value = "main"
    return BranchScreen(presenter), presenter


def _selection_event(prompt: str, option_id: str | None = None):
    return SimpleNamespace(option=SimpleNamespace(prompt=prompt, id=option_id))


class BranchApp(App):
    def __init__(self, branches: list[str]) -> None:
        super().__init__()
        self._presenter = Mock()
        self._presenter.get_branches.return_value = branches
        self._presenter.get_current_branch.return_value = "main"
        self.errors: list[str] = []

    def show_error(self, message: str) -> None:
        """Test double for GituxApp.show_error (skeleton K2)."""
        self.errors.append(message)

    def on_mount(self) -> None:
        self.push_screen(BranchScreen(self._presenter))


class TestSelectionHandler:
    def test_selection_switches_and_dismisses(self) -> None:
        screen, presenter = _make_screen()
        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.on_option_list_option_selected(
                _selection_event("feature/x", option_id="feature/x")
            )
        presenter.switch_branch.assert_called_once_with("feature/x")
        mock_dismiss.assert_called_once_with("Switched to feature/x")

    def test_selection_git_error_routes_to_error_line_and_stays_open(self) -> None:
        screen, presenter = _make_screen()
        presenter.switch_branch.side_effect = GitError("dirty working tree")
        mock_app = Mock()
        with patch.object(
            BranchScreen, "app", new_callable=_app_property(mock_app)
        ), patch.object(screen, "dismiss") as mock_dismiss:
            screen.on_option_list_option_selected(
                _selection_event("feature/x", option_id="feature/x")
            )
        mock_app.show_error.assert_called_once()
        call_message = mock_app.show_error.call_args[0][0]
        assert "branch switch failed" in call_message
        assert "dirty working tree" in call_message
        assert "(c)" in call_message  # the named next action
        mock_dismiss.assert_not_called()


def _app_property(mock_app):
    """Return a PropertyMock factory that always yields ``mock_app``."""
    def _factory(*_args, **_kwargs):
        from unittest.mock import PropertyMock
        return PropertyMock(return_value=mock_app)
    return _factory


class TestMountedFlow:
    @pytest.mark.asyncio
    async def test_populates_options_marks_current_and_focuses_list(self) -> None:
        app = BranchApp(["feature/x", "main"])
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.screen.__class__.__name__ == "BranchScreen"
            option_list = app.screen.query_one("#branch-option-list", OptionList)
            assert option_list.option_count == 2
            assert option_list.has_focus
            # The current branch is marked with ● (K3: current highlighted)
            prompts = [
                option_list.get_option_at_index(i).prompt
                for i in range(option_list.option_count)
            ]
            assert any("\u25cf main" in str(p) for p in prompts)
            # The name input starts hidden
            name_input = app.screen.query_one("#branch-name-input", Input)
            assert name_input.display is False

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


class TestMergeAction:
    @pytest.mark.asyncio
    async def test_merge_selected_into_current(self) -> None:
        app = BranchApp(["main", "feature/x"])
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            option_list = screen.query_one("#branch-option-list", OptionList)
            option_list.highlighted = 1  # feature/x
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.action_merge()
            app._presenter.merge_branch.assert_called_once_with("feature/x")
            mock_dismiss.assert_called_once_with("Merged feature/x into main")

    @pytest.mark.asyncio
    async def test_merge_current_into_itself_is_prevented(self) -> None:
        app = BranchApp(["main", "feature/x"])
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            option_list = screen.query_one("#branch-option-list", OptionList)
            option_list.highlighted = 0  # main (current)
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.action_merge()
            app._presenter.merge_branch.assert_not_called()
            mock_dismiss.assert_not_called()
            hint = screen.query_one("#branch-modal-hint", Static)
            assert "already on main" in str(hint.content)

    @pytest.mark.asyncio
    async def test_merge_conflict_routes_to_error_line(self) -> None:
        app = BranchApp(["main", "feature/x"])
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            app._presenter.merge_branch.side_effect = GitError(
                "Automatic merge failed; fix conflicts"
            )
            option_list = screen.query_one("#branch-option-list", OptionList)
            option_list.highlighted = 1
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.action_merge()
            mock_dismiss.assert_not_called()
            assert len(app.errors) == 1
            assert "merge failed" in app.errors[0]
            assert "resolve conflicts" in app.errors[0]


class TestDeleteAction:
    @pytest.mark.asyncio
    async def test_delete_requires_confirmation_then_y_confirms(self) -> None:
        app = BranchApp(["main", "feature/x"])
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            option_list = screen.query_one("#branch-option-list", OptionList)
            option_list.highlighted = 1
            # First d: asks for confirmation (prevention rung, T3)
            screen.action_delete()
            hint = screen.query_one("#branch-modal-hint", Static)
            assert "Delete 'feature/x'?" in str(hint.content)
            app._presenter.delete_branch.assert_not_called()
            # y confirms
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.action_confirm_delete()
            app._presenter.delete_branch.assert_called_once_with("feature/x")
            mock_dismiss.assert_called_once_with("Deleted feature/x")

    @pytest.mark.asyncio
    async def test_delete_current_branch_is_prevented(self) -> None:
        app = BranchApp(["main", "feature/x"])
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            option_list = screen.query_one("#branch-option-list", OptionList)
            option_list.highlighted = 0  # main (current)
            screen.action_delete()
            hint = screen.query_one("#branch-modal-hint", Static)
            assert "cannot delete main" in str(hint.content)
            app._presenter.delete_branch.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_unmerged_routes_to_error_line(self) -> None:
        app = BranchApp(["main", "feature/x"])
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            app._presenter.delete_branch.side_effect = GitError(
                "not fully merged"
            )
            option_list = screen.query_one("#branch-option-list", OptionList)
            option_list.highlighted = 1
            screen.action_delete()
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.action_confirm_delete()
            mock_dismiss.assert_not_called()
            assert len(app.errors) == 1
            assert "delete failed" in app.errors[0]


class TestNewBranchAction:
    @pytest.mark.asyncio
    async def test_new_shows_input_and_enter_creates(self) -> None:
        app = BranchApp(["main"])
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.action_new()
            await pilot.pause()
            name_input = screen.query_one("#branch-name-input", Input)
            assert name_input.display is True
            assert name_input.has_focus
            name_input.value = "feature/y"
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.on_input_submitted(SimpleNamespace())
            app._presenter.create_branch.assert_called_once_with("feature/y")
            mock_dismiss.assert_called_once_with("Created feature/y")

    @pytest.mark.asyncio
    async def test_new_branch_failure_routes_to_error_line(self) -> None:
        app = BranchApp(["main"])
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            app._presenter.create_branch.side_effect = GitError("invalid name")
            screen.action_new()
            name_input = screen.query_one("#branch-name-input", Input)
            name_input.value = "bad name!"
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.on_input_submitted(SimpleNamespace())
            mock_dismiss.assert_not_called()
            assert len(app.errors) == 1
            assert "create failed" in app.errors[0]
