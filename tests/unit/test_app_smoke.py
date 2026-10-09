import unittest.mock

import pytest
from textual.css.query import NoMatches

from gitux.domain import (
    CommitResult,
    FileStatus,
    HeadSummary,
    OperationState,
    PullResult,
    PushResult,
    RemoteStatus,
    RepoInfo,
)
from gitux.git import GitError
from gitux.git.status import BINARY_DIFF_MARKER
from gitux.ui.app import GituxApp, _BLOCK_MAP, _BLOCK_ORDER, _POLL_SECONDS
from gitux.ui.widgets import RepoStatsBar


@pytest.mark.asyncio
async def test_app_mounts_without_error():
    app = GituxApp()
    async with app.run_test() as pilot:
        assert app.query_one("#top-bar") is not None
        assert app.query_one("#stats-bar") is not None
        assert isinstance(app.query_one("#stats-bar"), RepoStatsBar)
        assert app.query_one("#main-content") is not None
        assert app.query_one("#bento-top") is not None
        assert app.query_one("#files-block") is not None
        assert app.query_one("#diff-block") is not None
        assert app.query_one("#changed-files") is not None
        assert app.query_one("#diff-viewer") is not None
        assert app.query_one("#commit-panel") is not None
        assert app.query_one("#error-line") is not None
        with pytest.raises(NoMatches):
            app.query_one("#sidebar")
        with pytest.raises(NoMatches):
            app.query_one("#workspace")
        with pytest.raises(NoMatches):
            app.query_one("#commits-block")
        with pytest.raises(NoMatches):
            app.query_one("#commit-log")


@pytest.mark.asyncio
async def test_files_block_active_on_mount_and_no_focus():
    app = GituxApp()
    async with app.run_test() as pilot:
        # The "files" block should be active after mount
        assert app._active_block == "files"
        # Focus is deliberately cleared so buttons don't intercept keys
        assert app.screen.focused is None


@pytest.mark.asyncio
async def test_header_displays_loading_state():
    app = GituxApp()
    async with app.run_test() as pilot:
        header = app.query_one("#top-bar")
        assert header is not None


def test_c_binding_removed():
    """K8: the ``c`` interaction is gone — Tab reaches the commit block."""
    assert "c" not in {binding.key for binding in GituxApp.BINDINGS}
    assert getattr(GituxApp, "action_open_commit", None) is None


@pytest.mark.asyncio
async def test_escape_returns_focus_to_board():
    """K8: ``Esc`` from the commit block returns to the files block."""
    app = GituxApp()
    async with app.run_test() as pilot:
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.pause()
        assert app._active_block == "commit"
        assert app.query_one("#commit-message").has_focus
        await pilot.press("escape")
        await pilot.pause()
        assert app._active_block == "files"
        assert app.screen.focused is None


@pytest.mark.asyncio
async def test_ctrl_enter_commits_from_panel():
    """K1/S5: Ctrl+Enter commits subject + body from the panel."""
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app, staged=True)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.pause()
        app.query_one("#commit-message").text = "feat: panel works\n\nlonger explanation"
        with unittest.mock.patch.object(
            app.presenter,
            "commit",
            return_value=CommitResult(success=True, commit_hash="abc1234"),
        ) as mock_commit:
            await pilot.press("ctrl+enter")
            await pilot.pause()
        mock_commit.assert_called_once_with("feat: panel works\n\nlonger explanation")
        assert app.query_one("#commit-message").text == ""


@pytest.mark.asyncio
async def test_empty_subject_routes_to_error_line():
    """T3 prevention: Ctrl+Enter with an empty subject names the fix."""
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app, staged=True)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.pause()
        await pilot.press("ctrl+enter")
        await pilot.pause()
        error_line = app.query_one("#error-line")
        assert error_line.display is True
        assert "message is empty" in str(error_line.content)
        assert "type a subject" in str(error_line.content)


@pytest.mark.asyncio
async def test_commit_nothing_staged_routes_to_error_line():
    """T3 prevention: committing with nothing staged names s/a."""
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app, staged=False)
        app.query_one("#commit-message").text = "feat: nothing staged"
        with unittest.mock.patch.object(
            app.presenter,
            "commit",
            return_value=CommitResult(success=False, error="No staged changes to commit"),
        ):
            app.commit_from_panel("feat: nothing staged", "")
        error_line = app.query_one("#error-line")
        assert error_line.display is True
        assert "nothing staged" in str(error_line.content)
        assert "stage with s" in str(error_line.content)


@pytest.mark.asyncio
async def test_commit_block_board_keys_do_not_move_panels():
    """K8: while the commit block holds the keyboard, board keys do
    nothing to the files panel (they type into the editor instead)."""
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.pause()
        changed_files = app.query_one("#changed-files")
        assert changed_files._cursor_index == 0
        for key in ("down", "up", "s", "a"):
            await pilot.press(key)
        assert changed_files._cursor_index == 0
        assert app._active_block == "commit"


@pytest.mark.asyncio
async def test_tab_cycles_three_blocks():
    """K8: Tab cycles files → diff → commit → files; the commit block
    illuminates (block-active) and its editor takes the keyboard."""
    app = GituxApp()
    async with app.run_test() as pilot:
        assert app._active_block == "files"
        await pilot.press("tab")
        assert app._active_block == "diff"
        await pilot.press("tab")
        assert app._active_block == "commit"
        panel = app.query_one("#commit-panel")
        assert "block-active" in panel.classes
        assert app.query_one("#commit-message").has_focus
        await pilot.press("tab")
        assert app._active_block == "files"
        assert "block-inactive" in panel.classes


def test_block_map_and_order():
    assert _BLOCK_ORDER == ("files", "diff", "commit")
    assert "commits" not in _BLOCK_MAP
    assert "commit" in _BLOCK_MAP


def test_no_manual_refresh_binding():
    """T1 (structure): the manual refresh key is gone — the board is live."""
    assert "r" not in {binding.key for binding in GituxApp.BINDINGS}
    assert getattr(GituxApp, "action_refresh", None) is None


def test_pull_binding_exists():
    """K4 (skeleton): pull is a direct board action on ``p``."""
    assert "p" in {binding.key for binding in GituxApp.BINDINGS}
    assert getattr(GituxApp, "action_pull", None) is not None


@pytest.mark.asyncio
async def test_refresh_failure_routes_to_error_line():
    """T4 (structure): a failed git command surfaces on the error line, never as silence."""
    app = GituxApp()
    async with app.run_test():
        error_line = app.query_one("#error-line")
        assert error_line.display is False
        with unittest.mock.patch.object(
            app.presenter, "load_status", side_effect=GitError("not a git repository")
        ):
            app._refresh_all()
        assert error_line.display is True
        content = str(error_line.content)
        assert "git failed" in content
        assert "not a git repository" in content
        assert "? for help" in content


@pytest.mark.asyncio
async def test_error_line_clears_on_next_successful_refresh():
    """K2 (skeleton): the error line clears on the next action."""
    app = GituxApp()
    async with app.run_test():
        app.show_error("something broke \u2192 press ? for help")
        error_line = app.query_one("#error-line")
        assert error_line.display is True
        app._refresh_all()  # the project repo is real — this refresh succeeds
        assert error_line.display is False


@pytest.mark.asyncio
async def test_push_rejection_names_pull_key():
    """T3's flagship case: a rejected push names ``p`` as the way forward."""
    app = GituxApp()
    async with app.run_test():
        result = PushResult(success=False, error="Remote has new changes. Pull first.")
        app._handle_push_result(result)
        error_line = app.query_one("#error-line")
        assert error_line.display is True
        content = str(error_line.content)
        assert "press p to pull" in content
        assert "ctrl+p" in content


@pytest.mark.asyncio
async def test_pull_diverged_names_merge_path():
    """A diverged pull names the branches screen as the way forward."""
    app = GituxApp()
    async with app.run_test():
        result = PullResult(success=False, error="branches diverged", diverged=True)
        app._handle_pull_result(result)
        error_line = app.query_one("#error-line")
        assert error_line.display is True
        content = str(error_line.content)
        assert "diverged" in content
        assert "(b)" in content


@pytest.mark.asyncio
async def test_poll_registered_on_mount():
    """T2 (structure): the live-board poll is registered at mount."""
    app = GituxApp()
    with unittest.mock.patch.object(GituxApp, "set_interval") as mock_set:
        async with app.run_test():
            mock_set.assert_called_once_with(_POLL_SECONDS, app._live_refresh)


@pytest.mark.asyncio
async def test_live_refresh_skips_while_modal_open():
    """The poll never fights an open modal for the board."""
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_branches", return_value=["a"]):
            await pilot.press("b")
        await pilot.pause()
        assert app.screen.is_modal
        with unittest.mock.patch.object(app, "_refresh_all") as mock_refresh:
            app._live_refresh()
        mock_refresh.assert_not_called()

        await pilot.press("escape")
        await pilot.pause()
        assert not app.screen.is_modal
        with unittest.mock.patch.object(app, "_refresh_all") as mock_refresh:
            app._live_refresh()
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_app_focus_triggers_refresh():
    """T2's focus rung: regaining terminal focus refreshes the board."""
    app = GituxApp()
    async with app.run_test():
        with unittest.mock.patch.object(app, "_refresh_all") as mock_refresh:
            app.on_app_focus()
        mock_refresh.assert_called_once()


def test_route_to_commits_deleted():
    assert getattr(GituxApp, "_route_to_commits", None) is None


@pytest.mark.asyncio
async def test_branch_screen_opens_on_b():
    app = GituxApp()
    async with app.run_test() as pilot:
        await pilot.press("b")
        assert app.screen.__class__.__name__ == "BranchScreen"
        assert app.screen.query_one("#branch-option-list") is not None


@pytest.mark.asyncio
async def test_branch_screen_cancels_on_escape():
    app = GituxApp()
    async with app.run_test() as pilot:
        await pilot.press("b")
        assert app.screen.__class__.__name__ == "BranchScreen"
        await pilot.press("escape")
        assert app.screen.__class__.__name__ != "BranchScreen"


@pytest.mark.asyncio
async def test_changed_files_autoscrolls_on_cursor_down():
    app = GituxApp()
    async with app.run_test() as pilot:
        files = [
            FileStatus(" ", "M", f"src/file_{i:03d}.py", None) for i in range(100)
        ]
        with unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status", return_value=files
        ):
            app._refresh_all()
        for _ in range(30):
            await pilot.press("down")
        changed_files = app.query_one("#changed-files")
        assert changed_files.scroll_y > 0


@pytest.mark.asyncio
async def test_refresh_all_wires_counts_strip():
    """K6: the stats line renders the counts strip, not subject/time."""
    app = GituxApp()
    async with app.run_test() as pilot:
        files = [
            FileStatus("M", " ", "staged.py", None),
            FileStatus(" ", "M", "mod.py", None),
            FileStatus("?", "?", "new.py", None),
        ]
        with unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status", return_value=files
        ), unittest.mock.patch.object(
            app.presenter, "staged_numstat", return_value=(10, 2)
        ):
            app._refresh_all()
        left = str(app.query_one("#stats-left").content)
        assert "STAGED (1, +10 -2)" in left
        assert "UNSTAGED (1)" in left
        assert "UNTRACKED (1)" in left
        # the old orientation content is gone (S6 amended)
        assert "no commits" not in left


def _seed_files(app, count: int = 30, staged: bool = False) -> None:
    index_status = "M" if staged else " "
    files = [
        FileStatus(index_status, "M", f"src/file_{i:03d}.py", None) for i in range(count)
    ]
    with unittest.mock.patch(
        "gitux.presenter.commit_presenter.get_status", return_value=files
    ):
        app._refresh_all()


@pytest.mark.asyncio
async def test_modal_open_branch_arrows_do_not_scroll_files():
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app)
        with unittest.mock.patch.object(
            app.repo, "get_branches", return_value=["a", "b", "c"]
        ), unittest.mock.patch.object(
            app.repo, "get_current_branch", return_value="a"
        ):
            await pilot.press("b")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "BranchScreen"
        changed_files = app.query_one("#changed-files")
        option_list = app.screen.query_one("#branch-option-list")
        assert changed_files._cursor_index == 0
        assert changed_files.scroll_y == 0
        for _ in range(3):
            await pilot.press("down")
        assert changed_files._cursor_index == 0
        assert changed_files.scroll_y == 0
        assert option_list.highlighted == 2


@pytest.mark.asyncio
async def test_modal_open_tab_does_not_cycle_blocks():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(
            app.repo, "get_branches", return_value=["a"]
        ), unittest.mock.patch.object(
            app.repo, "get_current_branch", return_value="a"
        ):
            await pilot.press("b")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "BranchScreen"
        assert app._block_index == 0
        await pilot.press("tab")
        assert app._block_index == 0
        assert app._active_block == "files"


@pytest.mark.asyncio
async def test_blocks_bordered_and_aligned_at_mount():
    app = GituxApp()
    async with app.run_test(size=(100, 40)) as pilot:
        for block_id in ("#files-block", "#diff-block"):
            block = app.query_one(block_id)
            assert len(block.classes & {"block-active", "block-inactive"}) == 1
            assert block.styles.border.top[0] == "round"
        files_header = app.query_one("#files-block").query_one(".block-header")
        diff_header = app.query_one("#diff-block").query_one(".block-header")
        assert files_header.region.y == diff_header.region.y
        assert files_header.region.y == 4
        assert diff_header.region.y == 4


@pytest.mark.asyncio
async def test_block_headers_subtitle_only():
    app = GituxApp()
    async with app.run_test() as pilot:
        assert app.query_one("#files-block")._title == ""
        assert app.query_one("#diff-block")._title == ""
        _seed_files(app, count=30)
        assert (
            app.query_one("#files-block").query_one(".block-header").content
            == "30 items"
        )
        changed_files = app.query_one("#changed-files")
        changed_files._cursor_index = 999
        with unittest.mock.patch.object(
            app.presenter, "get_staged_preview", return_value=""
        ):
            app._on_file_selected()
        assert (
            app.query_one("#diff-block").query_one(".block-header").content
            == "staged diff"
        )
        changed_files._cursor_index = 0
        with unittest.mock.patch.object(
            app.presenter, "get_diff", return_value="diff"
        ):
            app._on_file_selected()
        assert (
            app.query_one("#diff-block").query_one(".block-header").content
            == "src/file_000.py"
        )


@pytest.mark.asyncio
async def test_file_selected_distinguishes_binary_from_empty():
    """Binary files show the binary placeholder; empty files show the generic one."""
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app, count=1)
        changed_files = app.query_one("#changed-files")
        diff_viewer = app.query_one("#diff-viewer")
        changed_files._cursor_index = 0

        with unittest.mock.patch.object(
            app.presenter, "get_diff", return_value=BINARY_DIFF_MARKER
        ):
            app._on_file_selected()
        rendered = [strip.text for strip in diff_viewer.lines if strip.text]
        assert "Binary file, no diff available" in rendered[0]

        with unittest.mock.patch.object(app.presenter, "get_diff", return_value=""):
            app._on_file_selected()
        rendered = [strip.text for strip in diff_viewer.lines if strip.text]
        assert "No diff available" in rendered[0]
        assert "Binary" not in rendered[0]


@pytest.mark.asyncio
async def test_refresh_all_wires_steps_staged():
    """Staged files light the first step dot."""
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status",
            return_value=[FileStatus("M", " ", "a.py", None)],
        ), \
            unittest.mock.patch.object(
                app.repo,
                "get_head_summary",
                return_value=HeadSummary("66f7291", "feat: x", 1785784746),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ):
            app._refresh_all()
        stats = app.query_one("#stats-bar")
        assert stats._steps == 1
        steps_plain = stats.query_one("#stats-steps").content.plain
        assert steps_plain.count("\u25cf") == 1
        assert steps_plain.count("\u25cb") == 2


@pytest.mark.asyncio
async def test_refresh_all_wires_steps_fully_synced():
    """Clean tree + synced remote resets the indicator to 0."""
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status",
            return_value=[],
        ), \
            unittest.mock.patch.object(
                app.repo,
                "get_head_summary",
                return_value=HeadSummary("66f7291", "feat: x", 1785784746),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_remote_status",
                return_value=RemoteStatus("origin", "main", 0, 0),
            ):
            app._refresh_all()
        stats = app.query_one("#stats-bar")
        assert stats._steps == 0
        steps_plain = stats.query_one("#stats-steps").content.plain
        assert steps_plain.count("\u25cf") == 0
        assert steps_plain.count("\u25cb") == 3


@pytest.mark.asyncio
async def test_refresh_all_wires_steps_ahead_of_remote():
    """Committed but not pushed keeps the indicator at step 2."""
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status",
            return_value=[],
        ), \
            unittest.mock.patch.object(
                app.repo,
                "get_head_summary",
                return_value=HeadSummary("66f7291", "feat: x", 1785784746),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_remote_status",
                return_value=RemoteStatus("origin", "main", 2, 0),
            ):
            app._refresh_all()
        stats = app.query_one("#stats-bar")
        assert stats._steps == 2
        steps_plain = stats.query_one("#stats-steps").content.plain
        assert steps_plain.count("\u25cf") == 2
        assert steps_plain.count("\u25cb") == 1


@pytest.mark.asyncio
async def test_sync_segment_consistent_with_steps_ahead():
    """K6/V4: unpushed commits — dots at step 2 AND sync shows ↑2 (amber)."""
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status",
            return_value=[],
        ), \
            unittest.mock.patch.object(
                app.repo,
                "get_head_summary",
                return_value=HeadSummary("66f7291", "feat: x", 1785784746),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_remote_status",
                return_value=RemoteStatus("origin", "main", 2, 0),
            ):
            app._refresh_all()
        sync = str(app.query_one("#stats-sync").content)
        assert "\u21912 \u21930" in sync
        assert app.query_one("#stats-bar")._steps == 2


@pytest.mark.asyncio
async def test_sync_segment_consistent_with_steps_synced():
    """K6/V4: fully synced — dots reset to 0 AND sync shows ↑0 ↓0."""
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status",
            return_value=[],
        ), \
            unittest.mock.patch.object(
                app.repo,
                "get_head_summary",
                return_value=HeadSummary("66f7291", "feat: x", 1785784746),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_remote_status",
                return_value=RemoteStatus("origin", "main", 0, 0),
            ):
            app._refresh_all()
        sync = str(app.query_one("#stats-sync").content)
        assert "\u21910 \u21930" in sync
        assert app.query_one("#stats-bar")._steps == 0


@pytest.mark.asyncio
async def test_sync_segment_consistent_with_steps_behind():
    """K6/V4: behind remote — dots at step 3 AND sync shows ↓2."""
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch(
            "gitux.presenter.commit_presenter.get_status",
            return_value=[],
        ), \
            unittest.mock.patch.object(
                app.repo,
                "get_head_summary",
                return_value=HeadSummary("66f7291", "feat: x", 1785784746),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_remote_status",
                return_value=RemoteStatus("origin", "main", 0, 2),
            ):
            app._refresh_all()
        sync = str(app.query_one("#stats-sync").content)
        assert "\u21910 \u21932" in sync
        assert app.query_one("#stats-bar")._steps == 3


@pytest.mark.asyncio
async def test_commit_message_capped_at_400_chars():
    """The commit message has a hard 400-char cap (owner decision)."""
    app = GituxApp()
    async with app.run_test() as pilot:
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.pause()
        editor = app.query_one("#commit-message")
        editor.text = "x" * 500
        await pilot.pause()
        assert len(editor.text) == 400
        affordance = app.query_one("#commit-affordance")
        assert "400/400" in str(affordance.content)


@pytest.mark.asyncio
async def test_jk_move_cursor_in_files_block():
    """K10: j/k navigate like the arrows (the help documents them)."""
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app, count=5)
        changed_files = app.query_one("#changed-files")
        assert changed_files._cursor_index == 0
        await pilot.press("j")
        assert changed_files._cursor_index == 1
        await pilot.press("j")
        assert changed_files._cursor_index == 2
        await pilot.press("k")
        assert changed_files._cursor_index == 1
