"""Tests for gitux.ui.widgets.commit_screen.CommitScreen."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from textual.app import App
from textual.widgets import Button, Input, Static

from gitux.domain import CommitResult
from gitux.ui.widgets.commit_screen import _COMMIT_TYPES, CommitScreen


class CommitApp(App):
    def __init__(self, commit_result: CommitResult | None = None) -> None:
        super().__init__()
        self.presenter = Mock()
        self.presenter.commit.return_value = commit_result or CommitResult(
            success=True, commit_hash="abc1234"
        )

    def on_mount(self) -> None:
        self.push_screen(CommitScreen(self.presenter))


class TestStripTypePrefix:
    def test_known_prefix_stripped(self) -> None:
        assert CommitScreen._strip_type_prefix("feat: add parser") == "add parser"

    def test_different_known_prefix_stripped(self) -> None:
        assert CommitScreen._strip_type_prefix("feat: x") == "x"

    def test_no_colon_untouched(self) -> None:
        assert CommitScreen._strip_type_prefix("fix this") == "fix this"

    def test_multiline_known_prefix_stripped(self) -> None:
        assert CommitScreen._strip_type_prefix("feat: title\nbody") == "title\nbody"

    def test_unknown_prefix_untouched(self) -> None:
        assert CommitScreen._strip_type_prefix("random: stuff") == "random: stuff"


class TestMounted:
    @pytest.mark.asyncio
    async def test_labels_exact(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert (
                screen.query_one("#commit-modal-btn-commit", Button).label.plain
                == "Commit (Enter)"
            )
            assert (
                screen.query_one("#commit-modal-btn-cancel", Button).label.plain
                == "Cancel (Esc)"
            )

    @pytest.mark.asyncio
    async def test_type_row_defaults_to_feat(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert screen.query_one("#commit-modal-type", Static).content == "type: feat"
            assert screen._commit_type_index == 0

    @pytest.mark.asyncio
    async def test_cycle_type_wraps_forward_only(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            seen = []
            for _ in range(12):
                seen.append(screen.query_one("#commit-modal-type", Static).content)
                screen.action_cycle_type()
            assert seen == [f"type: {t}" for t in _COMMIT_TYPES] + ["type: feat"]
            assert screen._commit_type_index == 1  # 12 presses % 11 types

    @pytest.mark.asyncio
    async def test_tab_cycles_type_keeps_input_focus(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert screen.query_one("#commit-modal-input", Input).has_focus
            await pilot.press("tab")
            assert screen.query_one("#commit-modal-type", Static).content == "type: fix"
            assert screen.query_one("#commit-modal-input", Input).has_focus

    @pytest.mark.asyncio
    async def test_input_submitted_commits_with_prefix(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.query_one("#commit-modal-input", Input).value = "hello"
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.on_input_submitted(SimpleNamespace())
            app.presenter.commit.assert_called_once_with("feat: hello")
            mock_dismiss.assert_called_once_with("abc1234")

    @pytest.mark.asyncio
    async def test_other_commits_raw_message(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            while _COMMIT_TYPES[screen._commit_type_index] != "other":
                screen.action_cycle_type()
            screen.query_one("#commit-modal-input", Input).value = "hello world"
            with patch.object(screen, "dismiss"):
                screen.on_input_submitted(SimpleNamespace())
            app.presenter.commit.assert_called_once_with("hello world")

    @pytest.mark.asyncio
    async def test_no_prefix_duplication(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.query_one("#commit-modal-input", Input).value = "feat: add parser"
            with patch.object(screen, "dismiss"):
                screen.action_submit()
            app.presenter.commit.assert_called_once_with("feat: add parser")

    @pytest.mark.asyncio
    async def test_selected_fix_overrides_typed_feat(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.action_cycle_type()
            screen.query_one("#commit-modal-input", Input).value = "feat: x"
            with patch.object(screen, "dismiss"):
                screen.action_submit()
            app.presenter.commit.assert_called_once_with("fix: x")

    @pytest.mark.asyncio
    async def test_no_colon_prefixed(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.action_cycle_type()
            screen.query_one("#commit-modal-input", Input).value = "fix this"
            with patch.object(screen, "dismiss"):
                screen.action_submit()
            app.presenter.commit.assert_called_once_with("fix: fix this")

    @pytest.mark.asyncio
    async def test_multiline_message_prefixed(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.query_one("#commit-modal-input", Input).value = "feat: title\nbody"
            with patch.object(screen, "dismiss"):
                screen.action_submit()
            app.presenter.commit.assert_called_once_with("feat: title\nbody")

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
            app.presenter.commit.assert_called_once_with("feat: hello")
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
            app.presenter.commit.assert_called_once_with("feat: hello")

    @pytest.mark.asyncio
    async def test_enter_commits_when_commit_button_focused(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.query_one("#commit-modal-input", Input).value = "hello"
            screen.query_one("#commit-modal-btn-commit", Button).focus()
            await pilot.press("enter")
            app.presenter.commit.assert_called_once_with("feat: hello")

    @pytest.mark.asyncio
    async def test_escape_cancels_without_commit(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            assert app.screen.__class__.__name__ != "CommitScreen"
            app.presenter.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_shift_tab_is_not_backwards_cycle(self) -> None:
        app = CommitApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            await pilot.press("shift+tab")
            assert screen._commit_type_index == 0
            assert screen.query_one("#commit-modal-type", Static).content == "type: feat"

    @pytest.mark.asyncio
    async def test_modal_children_fit_at_80x24(self) -> None:
        app = CommitApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            screen = app.screen
            modal = screen.query_one("#commit-modal")
            for child_id in (
                "#commit-modal-title",
                "#commit-modal-type",
                "#commit-modal-input",
                "#commit-modal-buttons",
            ):
                child = screen.query_one(child_id)
                assert child.region.height >= 1
                assert modal.region.contains_region(child.region)
