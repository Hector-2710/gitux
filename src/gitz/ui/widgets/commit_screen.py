"""Commit screen modal — centered overlay for writing commit messages."""

import re
from typing import override

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from gitz.presenter.commit_presenter import CommitPresenter

_COMMIT_TYPES: tuple[str, ...] = (
    "feat", "fix", "chore", "docs", "style", "refactor", "perf", "test",
    "build", "ci", "other",
)
_PREFIX_RE: re.Pattern[str] = re.compile(r"^([a-z]+):\s*(.*)$", re.DOTALL)


class CommitScreen(ModalScreen[str]):
    """Modal screen for entering a commit message.

    Opens centered when pressing 'c'.
    Returns the commit hash on success, or None if cancelled/failed.
    """

    BINDINGS: list[Binding] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Commit"),
        Binding("tab", "cycle_type", "Next type", show=False),
    ]

    def __init__(self, presenter: CommitPresenter) -> None:
        super().__init__()
        self.presenter: CommitPresenter = presenter
        self._commit_type_index: int = 0

    @override
    def compose(self) -> ComposeResult:
        """Build the modal: title, type row, message input, and buttons."""
        with Vertical(id="commit-modal"):
            yield Static("Commit Changes", id="commit-modal-title")
            yield Static(f"type: {_COMMIT_TYPES[0]}", id="commit-modal-type")
            yield Input(
                placeholder="Commit message...",
                id="commit-modal-input",
            )
            with Horizontal(id="commit-modal-buttons"):
                yield Button("Commit (Enter)", id="commit-modal-btn-commit")
                yield Button("Cancel (Esc)", id="commit-modal-btn-cancel")

    def on_mount(self) -> None:
        """Focus the commit input immediately."""
        _ = self.query_one("#commit-modal-input", Input).focus()

    def action_cancel(self) -> None:
        """Dismiss the modal without committing."""
        _ = self.dismiss(None)

    def action_submit(self) -> None:
        """Commit the current message."""
        self._do_commit()

    def action_cycle_type(self) -> None:
        """Advance the type forward only; wraps from 'other' back to 'feat'."""
        self._commit_type_index = (self._commit_type_index + 1) % len(_COMMIT_TYPES)
        _ = self.query_one("#commit-modal-type", Static).update(
            f"type: {_COMMIT_TYPES[self._commit_type_index]}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Commit or cancel based on the pressed button."""
        if event.button.id == "commit-modal-btn-commit":
            self._do_commit()
        elif event.button.id == "commit-modal-btn-cancel":
            self.action_cancel()

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

        commit_type = _COMMIT_TYPES[self._commit_type_index]
        message = self._strip_type_prefix(message)
        if commit_type != "other":
            message = f"{commit_type}: {message}"

        result = self.presenter.commit(message)

        if result.success:
            _ = self.dismiss(result.commit_hash)
        else:
            _ = self.notify(result.error or "Commit failed", severity="error")

    @staticmethod
    def _strip_type_prefix(message: str) -> str:
        """Remove a leading '<known-type>:' so selecting that type does not duplicate it."""
        match = _PREFIX_RE.match(message)
        if match and match.group(1) in _COMMIT_TYPES:
            return match.group(2)
        return message
