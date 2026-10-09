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
    PullResult,
    PushResult,
    RemoteStatus,
    RepoInfo,
    derive_steps,
    derive_wip_state,
)
from gitux.git import GitError
from gitux.git.status import BINARY_DIFF_MARKER
from gitux.presenter.commit_presenter import CommitPresenter
from gitux.presenter.repo_presenter import RepoPresenter
from gitux.ui.widgets import (
    BlockContainer,
    BranchScreen,
    ChangedFilesPanel,
    CommitLogScreen,
    CommitPanel,
    DiffViewerWidget,
    ErrorLine,
    HelpScreen,
    RepoStatsBar,
    TopAppBar,
)

_CSS_PATH: str = str(Path(__file__).parent / "gitux.tcss")

_BLOCK_MAP: dict[str, dict[str, str]] = {
    "files":   {"block": "#files-block",   "content": "#changed-files"},
    "diff":    {"block": "#diff-block",    "content": "#diff-viewer"},
    "commit":  {"block": "#commit-panel",  "content": "#commit-message"},
}

_BLOCK_ORDER: tuple[str, ...] = ("files", "diff", "commit")

_POLL_SECONDS: float = 3.0
"""Background poll interval (structure T2): keeps the board true even when
the user only watches (e.g., an editor saving in another pane)."""


class GituxApp(App[None]):
    """Main Textual application for GITUX.

    Composes a two-panel layout with:
    - TopAppBar header (repo name, branch)
    - RepoStatsBar (repo stats + commit-step indicator)
    - Two BlockContainers: Changed Files, File Diff

    The board is live (scope S13 / structure T1-T2): repository state
    refreshes after every action, when the terminal regains focus, and on a
    background poll — there is no manual refresh key.

    Owns :class:`RepoPresenter` and :class:`CommitPresenter` and coordinates
    data flow between them and the widget layer.
    """

    CSS_PATH = _CSS_PATH

    # Focus is deliberate (skeleton K1/K8): the board blurs on mount, ``c``
    # focuses the commit panel, modals focus their own lists. Textual's
    # auto-focus would grab the commit subject input and steal the board's
    # keys — so it is disabled app-wide.
    AUTO_FOCUS = None

    BINDINGS = [
        Binding("ctrl+p", "push", "Push", show=True),
        Binding("p", "pull", "Pull", show=True),
        Binding("b", "open_branches", "Branches", show=True),
        Binding("l", "open_commit_log", "Log", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("question_mark", "help", "Help", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._active_block: str = "files"
        self._block_index: int = 0
        self._error_line: ErrorLine | None = None
        self._commit_panel: CommitPanel | None = None
        self.repo = RepoPresenter()
        self.presenter = CommitPresenter()

    def compose(self) -> ComposeResult:
        """Build the widget tree: header, stats bar, bento grid, error line, commit panel."""
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
        yield ErrorLine(id="error-line")
        yield CommitPanel(id="commit-panel")

    def on_mount(self) -> None:
        """Initialise data, activate the files block, start the live-board poll."""
        self._error_line = self.query_one("#error-line", ErrorLine)
        self._commit_panel = self.query_one("#commit-panel", CommitPanel)
        self._refresh_all()
        self._activate_block("files")
        self.set_interval(_POLL_SECONDS, self._live_refresh)

    def show_error(self, message: str) -> None:
        """Route an error to the persistent error line (skeleton K2 / T3).

        The message must name the next action and its key.
        """
        if self._error_line is not None:
            self._error_line.show(message)

    def clear_error(self) -> None:
        """Hide the error line — called at the start of every action (K2)."""
        if self._error_line is not None:
            self._error_line.clear()

    def commit_from_panel(self, subject: str, body: str) -> None:
        """Commit from the permanent panel (K1). Errors route per T3.

        Subject is required; body is optional (scope S5: multi-line).
        """
        message = subject.strip()
        if body.strip():
            message = f"{message}\n\n{body.strip()}"

        if not message:
            self.show_error(
                "commit blocked: message is empty \u2192 type a subject, then ctrl+enter"
            )
            return

        result = self.presenter.commit(message)

        if result.success:
            if self._commit_panel is not None:
                self._commit_panel.clear_inputs()
            self.notify(f"Committed: {result.commit_hash}", severity="information")
            self.return_focus_to_board()
            self._refresh_all()
        elif result.error and "No staged changes" in result.error:
            self.show_error(
                "commit blocked: nothing staged \u2192 stage with s (file) or a (all), then ctrl+enter"
            )
        else:
            self.show_error(
                f"commit failed: {result.error or 'unknown error'} \u2192 check the message, then ctrl+enter"
            )

    def return_focus_to_board(self) -> None:
        """Leave the commit panel: activate the files block (K8)."""
        self._activate_block("files")

    def action_push(self) -> None:
        """Push commits to remote (bound to ``ctrl+p``)."""
        self._run_push_worker()

    def action_pull(self) -> None:
        """Pull from the remote (bound to ``p`` — scope S4, skeleton K4)."""
        self._run_pull_worker()

    def _live_refresh(self) -> None:
        """Automatic refresh (structure T2: poll + terminal focus).

        Skipped while a modal screen is open — modals own the interaction
        and the board refreshes when they close.
        """
        if self.screen.is_modal:
            return
        self._refresh_all()

    def on_app_focus(self) -> None:
        """Refresh when the terminal regains focus (T2's focus rung).

        Only fires in terminals that support focus reporting; the background
        poll covers the rest.
        """
        self._live_refresh()

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

    def _handle_branch_selected(self, message: str | None) -> None:
        """Callback after the branch modal closes; refresh on success."""
        if message:
            self.notify(message, severity="information")
            self._refresh_all()

    def action_cycle_block(self, direction: int = 1) -> None:
        """Tab/Shift+Tab: cycle the board's blocks (K8) — files, diff, commit.

        Guarded against modals. Tab cycles even FROM the commit editor —
        that is the way out of the panel.
        """
        if self.screen.is_modal:
            return
        count = len(_BLOCK_ORDER)
        self._block_index = (self._block_index + direction) % count
        self._activate_block(_BLOCK_ORDER[self._block_index])

    def action_focus_next(self) -> None:
        """Tab is the board's block cycle (K8) — shadows Textual's focus walk.

        The base Screen binds ``tab → app.focus_next``; overriding the action
        here keeps Tab from walking focus into the commit panel's inputs.
        """
        self.action_cycle_block(direction=1)

    def action_focus_previous(self) -> None:
        """Shift+Tab cycles the board's blocks backward (K8)."""
        self.action_cycle_block(direction=-1)

    def on_key(self, event: Key) -> None:
        """Route keys: navigational keys go to the active panel."""
        if self.screen.is_modal:
            return
        if self._commit_panel is not None and self._commit_panel.has_keyboard():
            return  # the commit panel owns the keyboard (K1)

        key = event.key

        # ── All other navigational keys: route to active content panel ──
        if key in ("up", "down", "enter", "escape", "s", "a", "A", "j", "k",
                    "page_up", "page_down", "home", "end"):
            event.stop()
            routed = {"j": "down", "k": "up"}.get(key, key)
            self._route_key_to_panel(routed)

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
        """Activate a board block and deactivate the current one.

        Updates block border styles (the active block illuminates, K8) and
        hands the keyboard over: the commit block's editor takes focus;
        the files/diff blocks clear focus so keys route through on_key.
        """
        info = _BLOCK_MAP[block_name]

        if self._active_block:
            current_info = _BLOCK_MAP[self._active_block]
            current_block = self.query_one(current_info["block"])
            current_block.set_active(False)

        self._active_block = block_name
        self._block_index = _BLOCK_ORDER.index(block_name)

        new_block = self.query_one(info["block"])
        new_block.set_active(True)

        if block_name == "commit":
            # The commit block's editor owns the keyboard while active (K1).
            if self._commit_panel is not None:
                self._commit_panel.focus_message()
        else:
            # Clear keyboard focus so no widget can intercept subsequent keys.
            # set_focus(None) — blur() would ADVANCE focus to the next widget.
            self.screen.set_focus(None)

    @work(thread=True, exclusive=True)
    async def _run_push_worker(self) -> None:
        """Run push in a background thread to avoid blocking the UI."""
        result = self.presenter.push()
        self.call_from_thread(self._handle_push_result, result)

    @work(thread=True, exclusive=True)
    async def _run_pull_worker(self) -> None:
        """Run pull in a background thread to avoid blocking the UI."""
        result = self.presenter.pull()
        self.call_from_thread(self._handle_pull_result, result)

    def _handle_push_result(self, result: PushResult) -> None:
        """Route the push outcome: success toasts, failures to the error line (T3)."""
        self._refresh_all()
        if result.success:
            self.notify("Pushed successfully", severity="information")
            return
        if result.error and "Pull first" in result.error:
            # T3's flagship case: the error names the way forward and its key.
            self.show_error(
                "push rejected: remote moved forward \u2192 press p to pull, then ctrl+p push"
            )
        else:
            self.show_error(
                f"push failed: {result.error or 'unknown error'} \u2192 check remote access, then ? for help"
            )

    def _handle_pull_result(self, result: PullResult) -> None:
        """Route the pull outcome: success toasts, failures to the error line (T3)."""
        self._refresh_all()
        if result.success:
            self.notify("Pulled successfully", severity="information")
            return
        if result.diverged:
            self.show_error(
                "pull rejected: branches diverged \u2192 merge from the branches screen (b)"
            )
        else:
            self.show_error(
                f"pull failed: {result.error or 'unknown error'} \u2192 check remote access, then ? for help"
            )

    def _refresh_all(self) -> None:
        """Refresh every widget from git state: files, header, stats bar, log, diff.

        Structure T4 (no silent failures): git errors surface on the error
        line, never as empty data. The error line clears at the start of
        every action (skeleton K2).
        """
        self.clear_error()
        try:
            files = self.presenter.load_status()
        except GitError as exc:
            self.show_error(
                f"git failed: {exc} \u2192 check the repository, then ? for help"
            )
            return
        except Exception as exc:  # noqa: BLE001 — anything else also surfaces (T4)
            self.show_error(f"internal error: {exc} \u2192 press ? for help")
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
        steps = derive_steps(
            file_counts,
            remote_status,
            has_commits=head_summary is not None,
            operation=operation,
        )
        stats_bar.update_stats(
            counts=file_counts,
            staged_stat=self.presenter.staged_numstat(),
            remote_status=remote_status,
            steps=steps,
        )

        if self._commit_panel is not None:
            target = (
                f"{remote_status.remote}/{remote_status.branch}"
                if remote_status is not None and remote_status.remote
                else ""
            )
            self._commit_panel.update_context(branch=branch, target=target)

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
        except GitError as exc:
            self.show_error(
                f"staging failed: {exc} \u2192 check file permissions, then ? for help"
            )
        except Exception as exc:  # noqa: BLE001 — anything else also surfaces (T4)
            self.show_error(f"internal error: {exc} \u2192 press ? for help")

    def _on_stage_all(self) -> None:
        """Stage all unstaged files, then refresh."""
        try:
            unstaged = self.presenter.unstaged_files
            if unstaged:
                self.presenter.stage_files([f.path for f in unstaged])
                self._refresh_all()
        except GitError as exc:
            self.show_error(
                f"staging failed: {exc} \u2192 check file permissions, then ? for help"
            )
        except Exception as exc:  # noqa: BLE001 — anything else also surfaces (T4)
            self.show_error(f"internal error: {exc} \u2192 press ? for help")

    def _on_unstage_all(self) -> None:
        """Unstage all staged files, then refresh."""
        try:
            staged = self.presenter.staged_files
            if staged:
                self.presenter.unstage_files([f.path for f in staged])
                self._refresh_all()
        except GitError as exc:
            self.show_error(
                f"unstaging failed: {exc} \u2192 check file permissions, then ? for help"
            )
        except Exception as exc:  # noqa: BLE001 — anything else also surfaces (T4)
            self.show_error(f"internal error: {exc} \u2192 press ? for help")

    def _get_branch_safe(self) -> str:
        """Return the current branch name. Propagates GitError (caught by _refresh_all)."""
        return self.repo.get_current_branch()

    def _get_head_summary_safe(self) -> HeadSummary | None:
        """Return the HEAD summary (None for an empty repo). Propagates GitError."""
        return self.repo.get_head_summary()

    def _get_default_branch_safe(self) -> str:
        """Return the default branch name. Propagates GitError."""
        return self.repo.get_default_branch()

    def _get_operation_state_safe(self) -> OperationState | None:
        """Return the merge/rebase operation state. Propagates GitError."""
        return self.repo.get_operation_state()

    def _get_remote_status_safe(self) -> RemoteStatus | None:
        """Return remote status (``remote=""`` when no upstream). Propagates GitError."""
        return self.repo.get_remote_status()

    def _get_repo_info_safe(self) -> RepoInfo | None:
        """Return repo info. Propagates GitError."""
        return self.repo.get_repo_info()

    def _get_detached_safe(self) -> bool:
        """Return whether HEAD is detached. Propagates GitError."""
        return self.repo.is_detached_head()


if __name__ == "__main__":
    app = GituxApp()
    app.run()
