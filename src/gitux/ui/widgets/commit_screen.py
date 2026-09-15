"""Commit screen modal — centered overlay for writing commit messages."""

from typing import override

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from gitux.presenter.commit_presenter import CommitPresenter


class CommitScreen(ModalScreen[str]):
    """Modal screen for entering a commit message.

    Opens centered when pressing 'c'.
    Returns the commit hash on success, or None if cancelled/failed.
    """

    BINDINGS: list[Binding] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Commit"),
    ]

    def __init__(self, presenter: CommitPresenter) -> None:
        super().__init__()
        self.presenter: CommitPresenter = presenter

    @override
    def compose(self) -> ComposeResult:
        """Build the modal: title and message input."""
        with Vertical(id="commit-modal"):
            yield Static("Commit Changes", id="commit-modal-title")
            yield Input(
                placeholder="Commit message...",
                id="commit-modal-input",
            )

    def on_mount(self) -> None:
        """Focus the commit input immediately."""
        _ = self.query_one("#commit-modal-input", Input).focus()

    def action_cancel(self) -> None:
        """Dismiss the modal without committing."""
        _ = self.dismiss(None)

    def action_submit(self) -> None:
        """Commit the current message."""
        self._do_commit()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Submit the commit when Enter is pressed in the message input."""
        self._do_commit()

    def _do_commit(self) -> None:
        """Validate the message and run the commit, dismissing on success."""
        commit_input = self.query_one("#commit-modal-input", Input)
        message = commit_input.value.strip()

        if not message:
            _ = self.notify("Commit message cannot be empty", severity="error")
            return

        result = self.presenter.commit(message)

        if result.success:
            _ = self.dismiss(result.commit_hash)
        else:
            _ = self.notify(result.error or "Commit failed", severity="error")
