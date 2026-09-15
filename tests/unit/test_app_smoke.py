import unittest.mock

import pytest
from textual.css.query import NoMatches

from gitux.domain import FileStatus, HeadSummary, OperationState, RepoInfo
from gitux.ui.app import GituxApp, _BLOCK_MAP, _BLOCK_ORDER
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
        assert app.query_one("GituxFooter") is not None
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


@pytest.mark.asyncio
async def test_commit_screen_opens_on_c():
    app = GituxApp()
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert app.screen.__class__.__name__ == "CommitScreen"
        commit_input = app.screen.query_one("#commit-modal-input")
        assert commit_input.has_focus


@pytest.mark.asyncio
async def test_commit_screen_cancels_on_escape():
    app = GituxApp()
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert app.screen.__class__.__name__ == "CommitScreen"
        await pilot.press("escape")
        assert app.screen.__class__.__name__ != "CommitScreen"


@pytest.mark.asyncio
async def test_enter_in_commit_modal_empty_input_no_toggle():
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app)
        await pilot.press("c")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "CommitScreen"
        changed_files = app.query_one("#changed-files")
        cursor_before = changed_files._cursor_index
        with unittest.mock.patch.object(app, "notify") as mock_notify:
            await pilot.press("enter")
        assert changed_files._cursor_index == cursor_before
        assert app._active_block == "files"
        assert app.screen.__class__.__name__ == "CommitScreen"
        assert mock_notify.call_count == 1
        assert "cannot be empty" in mock_notify.call_args[0][0]


@pytest.mark.asyncio
async def test_tab_cycles_two_blocks():
    app = GituxApp()
    async with app.run_test() as pilot:
        assert app._active_block == "files"
        await pilot.press("tab")
        assert app._active_block == "diff"
        await pilot.press("tab")
        assert app._active_block == "files"
        await pilot.press("tab")
        assert app._active_block == "diff"


def test_block_map_and_order():
    assert _BLOCK_ORDER == ("files", "diff")
    assert "commits" not in _BLOCK_MAP


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
async def test_refresh_all_wires_new_bar_data():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_user", return_value="hector"), \
            unittest.mock.patch.object(app.repo, "get_head_summary", return_value=None), \
            unittest.mock.patch.object(app.repo, "get_default_branch", return_value=""), \
            unittest.mock.patch.object(
                app.repo,
                "get_repo_info",
                return_value=RepoInfo(name="gitux", path="/home/user/gitux"),
            ), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ):
            app._refresh_all()
        stats = app.query_one("#stats-bar")
        left = stats.query_one("#stats-left")
        header = app.query_one("#top-bar")
        assert left.content.plain.startswith("gitux")
        assert "gitux" in left.content.plain
        assert "hector" not in left.content.plain
        assert "(no commits)" in left.content.plain
        assert " \u25cf" in header.content.plain  # WIP dot always present


@pytest.mark.asyncio
async def test_refresh_all_without_repo_info_omits_repo_segment():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_user", return_value="hector"), \
            unittest.mock.patch.object(app.repo, "get_head_summary", return_value=None), \
            unittest.mock.patch.object(app.repo, "get_default_branch", return_value=""), \
            unittest.mock.patch.object(app.repo, "get_repo_info", return_value=None), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ):
            app._refresh_all()
        stats = app.query_one("#stats-bar")
        left = stats.query_one("#stats-left")
        assert "gitux" not in left.content.plain
        assert "hector" not in left.content.plain


def _seed_files(app, count: int = 30) -> None:
    files = [
        FileStatus(" ", "M", f"src/file_{i:03d}.py", None) for i in range(count)
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
async def test_modal_open_commit_keys_do_not_move_panels():
    app = GituxApp()
    async with app.run_test() as pilot:
        _seed_files(app)
        await pilot.press("c")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "CommitScreen"
        changed_files = app.query_one("#changed-files")
        assert changed_files._cursor_index == 0
        assert app._block_index == 0
        assert app._active_block == "files"
        for key in ("down", "up", "tab"):
            await pilot.press(key)
        assert changed_files._cursor_index == 0
        assert app._block_index == 0
        assert app._active_block == "files"


@pytest.mark.asyncio
async def test_modal_open_tab_does_not_cycle_blocks():
    app = GituxApp()
    async with app.run_test() as pilot:
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
async def test_refresh_all_wires_head_hash():
    app = GituxApp()
    async with app.run_test() as pilot:
        with unittest.mock.patch.object(app.repo, "get_user", return_value=""), \
            unittest.mock.patch.object(
                app.repo,
                "get_head_summary",
                return_value=HeadSummary("66f7291", "feat: x", 1785784746),
            ), \
            unittest.mock.patch.object(app.repo, "get_default_branch", return_value=""), \
            unittest.mock.patch.object(
                app.repo,
                "get_operation_state",
                return_value=OperationState(False, False),
            ):
            app._refresh_all()
        stats = app.query_one("#stats-bar")
        left = stats.query_one("#stats-left")
        assert "feat: x" in left.content.plain
