"""Commit log modal — full-width commit graph overlay opened with ``l``."""

from typing import override

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen

from gitux.presenter.repo_presenter import RepoPresenter
from gitux.ui.widgets.commit_log import CommitLogWidget, extract_commit_hash


class CommitLogScreen(ModalScreen[None]):
    """Modal showing the commit graph with per-commit details.

    Esc exits detail mode first, then dismisses the overlay.
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "show_detail", "Detail", show=False),
        Binding("escape", "close", "Close"),
        Binding("page_up", "page_up", "Page up", show=False),
        Binding("page_down", "page_down", "Page down", show=False),
        Binding("home", "home", "Home", show=False),
        Binding("end", "end", "End", show=False),
    ]

    def __init__(self, presenter: RepoPresenter) -> None:
        super().__init__()
        self.presenter: RepoPresenter = presenter

    @override
    def compose(self) -> ComposeResult:
        """Build the modal: a single commit-log widget inside the overlay."""
        with Vertical(id="commit-log-modal"):
            yield CommitLogWidget(id="commit-log")

    def on_mount(self) -> None:
        """Fetch a fresh commit log and render it or the empty state."""
        log = self.query_one("#commit-log", CommitLogWidget)
        text = self.presenter.get_commit_log(30)
        if text:
            log.show_log(text)
        else:
            log.clear()

    def action_cursor_down(self) -> None:
        """Move the cursor (log mode) or scroll (detail mode)."""
        log = self.query_one("#commit-log", CommitLogWidget)
        if log.is_detail_mode:
            log.scroll_down(animate=False)
        else:
            log.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move the cursor (log mode) or scroll (detail mode)."""
        log = self.query_one("#commit-log", CommitLogWidget)
        if log.is_detail_mode:
            log.scroll_up(animate=False)
        else:
            log.action_cursor_up()

    def action_show_detail(self) -> None:
        """Show commit details for the line under the cursor; no-op on graph lines."""
        log = self.query_one("#commit-log", CommitLogWidget)
        if log.is_detail_mode:
            return
        line = log.cursor_line
        if not line:
            return
        commit_hash = extract_commit_hash(line)
        if commit_hash is None:
            return
        details = self.presenter.get_commit_details(commit_hash)
        if not details:
            return
        log.show_details(commit_hash, details)

    def action_close(self) -> None:
        """Exit detail mode first, then dismiss the modal."""
        log = self.query_one("#commit-log", CommitLogWidget)
        if log.is_detail_mode:
            log.exit_details()
        else:
            _ = self.dismiss(None)

    def action_page_up(self) -> None:
        """Scroll up one page."""
        self.query_one("#commit-log", CommitLogWidget).scroll_page_up(animate=False)

    def action_page_down(self) -> None:
        """Scroll down one page."""
        self.query_one("#commit-log", CommitLogWidget).scroll_page_down(animate=False)

    def action_home(self) -> None:
        """Scroll to the top."""
        self.query_one("#commit-log", CommitLogWidget).scroll_home(animate=False)

    def action_end(self) -> None:
        """Scroll to the bottom."""
        self.query_one("#commit-log", CommitLogWidget).scroll_end(animate=False)