"""Main application — two-panel TUI for Git operations.

Composes the full UI layout, manages block activation (files/diff),
routes keyboard events, and orchestrates data flow between presenters and widgets.
"""

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key

from gitux.domain import (
    FileCounts,
    FileStatus,
    HeadSummary,
    OperationState,
    PushResult,
    RemoteStatus,
    RepoInfo,
    derive_wip_state,
)
from gitux.git.status import BINARY_DIFF_MARKER
from gitux.presenter.commit_presenter import CommitPresenter
from gitux.presenter.repo_presenter import RepoPresenter
from gitux.ui.widgets import (
    BlockContainer,
    BranchScreen,
    ChangedFilesPanel,
    CommitLogScreen,
    CommitScreen,
    DiffViewerWidget,
    GituxFooter,
    HelpScreen,
    RepoStatsBar,
    TopAppBar,
)

_CSS_PATH: str = str(Path(__file__).parent / "gitux.tcss")

_BLOCK_MAP: dict[str, dict[str, str]] = {
    "files":   {"block": "#files-block",   "content": "#changed-files"},
    "diff":    {"block": "#diff-block",    "content": "#diff-viewer"},
}

_BLOCK_ORDER: tuple[str, ...] = ("files", "diff")


class GituxApp(App[None]):
    """Main Textual application for GITUX.

    Composes a two-panel layout with:
    - TopAppBar header (repo name, branch)
    - RepoStatsBar (repo stats + commit-step indicator)
    - Two BlockContainers: Changed Files, File Diff
    - GituxFooter (shortcuts, version, sync status)

    Owns :class:`RepoPresenter` and :class:`CommitPresenter` and coordinates
    data flow between them and the widget layer.
    """

    CSS_PATH = _CSS_PATH

    BINDINGS = [
        Binding("ctrl+p", "push", "Push", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("c", "open_commit", "Commit", show=True),
        Binding("b", "open_branches", "Branches", show=True),
        Binding("l", "open_commit_log", "Log", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("question_mark", "help", "Help", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._active_block: str = "files"
        self._block_index: int = 0
        self.repo = RepoPresenter()
        self.presenter = CommitPresenter()

    def compose(self) -> ComposeResult:
        """Build the widget tree: header, stats bar, bento grid, footer."""
        yield TopAppBar(id="top-bar")
        yield RepoStatsBar(id="stats-bar")
        with Vertical(id="main-content"):
            with Horizontal(id="bento-top"):
                yield BlockContainer(
                    id="files-block",
                    title="",
                    subtitle="loading...",
                    content_widget=ChangedFilesPanel(id="changed-files"),
                )
                yield BlockContainer(
                    id="diff-block",
                    title="",
                    subtitle="staged diff",
                    content_widget=DiffViewerWidget(id="diff-viewer"),
                )
        yield GituxFooter()

    def on_mount(self) -> None:
        """Initialise data and activate the files block on startup."""
        self._refresh_all()
        self._activate_block("files")

    def action_open_commit(self) -> None:
        """Open the commit message modal (bound to ``c``)."""
        self.push_screen(
            CommitScreen(self.presenter),
            self._handle_commit_result,
        )

    def _handle_commit_result(self, commit_hash: str | None) -> None:
        """Callback after commit modal closes. Refresh on success."""
        if commit_hash:
            self.notify(f"Committed: {commit_hash}", severity="information")
            self._refresh_all()

    def action_push(self) -> None:
        """Push commits to remote (bound to ``ctrl+p``)."""
        self._run_push_worker()

    def action_refresh(self) -> None:
        """Refresh all panels from git (bound to ``r``)."""
        self._refresh_all()

    def action_help(self) -> None:
        """Show the keyboard-shortcuts help modal (bound to ``?``)."""
        self.push_screen(HelpScreen())

    def action_open_commit_log(self) -> None:
        """Open the commit log overlay (bound to ``l``)."""
        self.push_screen(CommitLogScreen(self.repo), lambda _result: None)

    def action_open_branches(self) -> None:
        """Open the branch-switch modal (bound to ``b``)."""
        self.push_screen(
            BranchScreen(self.repo),
            self._handle_branch_selected,
        )

    def _handle_branch_selected(self, branch: str | None) -> None:
        """Callback after the branch modal closes; refresh on success."""
        if branch:
            self.notify(f"Switched to {branch}", severity="information")
            self._refresh_all()

    def on_key(self, event: Key) -> None:
        """Route keys: Tab cycles+activates blocks, all others go to active panel."""
        if self.screen.is_modal:
            return
        key = event.key

        # ── Tab: cycle blocks and activate block immediately ──
        if key == "tab":
            event.stop()
            self._block_index = (self._block_index + 1) % len(_BLOCK_ORDER)
            self._activate_block(_BLOCK_ORDER[self._block_index])
            return

        # ── All other navigational keys: route to active content panel ──
        if key in ("up", "down", "enter", "escape", "s", "a", "A",
                    "page_up", "page_down", "home", "end"):
            event.stop()
            self._route_key_to_panel(key)

    def _route_key_to_panel(self, key: str) -> None:
        """Send a key event to the currently active content panel."""
        if self._active_block == "files":
            self._route_to_files(key)
        elif self._active_block == "diff":
            self._route_to_diff(key)

    def _route_to_files(self, key: str) -> None:
        """Route a key press to the changed-files panel."""
        panel = self.query_one("#changed-files", ChangedFilesPanel)
        if key == "down":
            panel.action_cursor_down()
        elif key == "up":
            panel.action_cursor_up()
        elif key in ("enter", "s"):
            panel.action_toggle_file()
        elif key == "a":
            panel.action_stage_all()
        elif key == "A":
            panel.action_unstage_all()

    def _route_to_diff(self, key: str) -> None:
        """Route a key press to the diff-viewer panel."""
        panel = self.query_one("#diff-viewer", DiffViewerWidget)
        if key == "down":
            panel.scroll_down(animate=False)
        elif key == "up":
            panel.scroll_up(animate=False)
        elif key == "page_down":
            panel.scroll_page_down(animate=False)
        elif key == "page_up":
            panel.scroll_page_up(animate=False)
        elif key == "home":
            panel.scroll_home(animate=False)
        elif key == "end":
            panel.scroll_end(animate=False)

    def _activate_block(self, block_name: str) -> None:
        """Activate a bento block and deactivate the current one.

        Updates block border styles and blurs keyboard focus so subsequent
        key events go through :meth:`on_key`.
        """
        info = _BLOCK_MAP[block_name]

        if self._active_block:
            current_info = _BLOCK_MAP[self._active_block]
            current_block = self.query_one(current_info["block"], BlockContainer)
            current_block.set_active(False)

        self._active_block = block_name
        self._block_index = _BLOCK_ORDER.index(block_name)

        new_block = self.query_one(info["block"], BlockContainer)
        new_block.set_active(True)

        # Clear keyboard focus so no widget can intercept subsequent keys
        if self.screen.focused is not None:
            self.screen.focused.blur()

    @work(thread=True, exclusive=True)
    async def _run_push_worker(self) -> None:
        """Run push in a background thread to avoid blocking the UI."""
        result = self.presenter.push()
        self.call_from_thread(self._handle_push_result, result)

    def _handle_push_result(self, result: PushResult) -> None:
        """Notify the user whether push succeeded or failed, then refresh."""
        if result.success:
            self.notify("Pushed successfully", severity="information")
        else:
            self.notify(result.error or "Push failed", severity="error")
        self._refresh_all()

    def _refresh_all(self) -> None:
        """Refresh every widget from git state: files, header, stats bar, log, diff, footer."""
        try:
            files = self.presenter.load_status()
        except Exception as exc:
            self.notify(f"Error loading status: {exc}", severity="error")
            return

        branch = self._get_branch_safe()
        remote_status = self._get_remote_status_safe()
        repo_info = self._get_repo_info_safe()
        is_detached = self._get_detached_safe()

        head_summary = self._get_head_summary_safe()
        default_branch = self._get_default_branch_safe()
        operation = self._get_operation_state_safe()

        file_counts = FileCounts.from_status(files)
        wip = derive_wip_state(
            file_counts,
            operation,
            has_commits=head_summary is not None,   # empty repo → UNKNOWN
        )

        header = self.query_one("#top-bar", TopAppBar)
        header.update_display(
            repo_name=repo_info.name if repo_info else "",
            owner=repo_info.owner if repo_info else "",
            branch=branch,
            is_detached=is_detached,
            default_branch=default_branch,
            wip_state=wip,
        )

        stats_bar = self.query_one("#stats-bar", RepoStatsBar)
        stats_bar.update_stats(
            repo_name=repo_info.name if repo_info else "",
            branch=branch,
            head_summary=head_summary,
        )

        changed_files = self.query_one("#changed-files", ChangedFilesPanel)
        changed_files.set_files(files)
        changed_files.set_on_toggle(self._on_file_toggle)
        changed_files.set_on_selection_change(self._on_file_selected)
        changed_files.set_on_stage_all(self._on_stage_all)
        changed_files.set_on_unstage_all(self._on_unstage_all)

        self.query_one("#files-block", BlockContainer).set_header_subtitle(
            f"{len(files)} items"
        )

        self._on_file_selected()

        footer = self.query_one(GituxFooter)
        sync_ok = remote_status is not None and remote_status.behind == 0
        footer.update_sync(ok=sync_ok)

    def _on_file_selected(self) -> None:
        """Update the diff viewer when the cursor moves to a different file."""
        changed_files = self.query_one("#changed-files", ChangedFilesPanel)
        diff_viewer = self.query_one("#diff-viewer", DiffViewerWidget)
        file = changed_files.selected_file

        if file is None:
            preview = self.presenter.get_staged_preview()
            if preview:
                diff_viewer.show_diff(preview)
            else:
                diff_viewer.clear()
            self.query_one("#diff-block", BlockContainer).set_header_subtitle("staged diff")
            return

        diff_text = self.presenter.get_diff(file)
        if diff_text == BINARY_DIFF_MARKER:
            diff_viewer.show_binary_placeholder()
        elif not diff_text:
            diff_viewer.show_no_diff_placeholder()
        else:
            diff_viewer.show_diff(diff_text)
        self.query_one("#diff-block", BlockContainer).set_header_subtitle(file.path)

    def _on_file_toggle(self, file: FileStatus) -> None:
        """Stage or unstage a single file, then refresh all panels."""
        try:
            if file.is_staged:
                self.presenter.unstage_files([file.path])
            else:
                self.presenter.stage_files([file.path])
            self._refresh_all()
        except Exception as exc:
            self.notify(f"Error: {exc}", severity="error")

    def _on_stage_all(self) -> None:
        """Stage all unstaged files, then refresh."""
        try:
            unstaged = self.presenter.unstaged_files
            if unstaged:
                self.presenter.stage_files([f.path for f in unstaged])
                self._refresh_all()
        except Exception as exc:
            self.notify(f"Error staging all: {exc}", severity="error")

    def _on_unstage_all(self) -> None:
        """Unstage all staged files, then refresh."""
        try:
            staged = self.presenter.staged_files
            if staged:
                self.presenter.unstage_files([f.path for f in staged])
                self._refresh_all()
        except Exception as exc:
            self.notify(f"Error unstaging all: {exc}", severity="error")

    def _get_branch_safe(self) -> str:
        """Return current branch name, or empty string on error."""
        return self.repo.get_current_branch()

    def _get_head_summary_safe(self) -> HeadSummary | None:
        """Return the HEAD commit summary, or None on error."""
        return self.repo.get_head_summary()

    def _get_default_branch_safe(self) -> str:
        """Return the default branch name, or empty string on error."""
        return self.repo.get_default_branch()

    def _get_operation_state_safe(self) -> OperationState | None:
        """Return the merge/rebase operation state, or None on error."""
        return self.repo.get_operation_state()

    def _get_remote_status_safe(self) -> RemoteStatus | None:
        """Return remote status, or ``None`` on error."""
        return self.repo.get_remote_status()

    def _get_repo_info_safe(self) -> RepoInfo | None:
        """Return repo info, or ``None`` on error."""
        return self.repo.get_repo_info()

    def _get_detached_safe(self) -> bool:
        """Return whether HEAD is detached (``False`` on error)."""
        return self.repo.is_detached_head()


if __name__ == "__main__":
    app = GituxApp()
    app.run()
