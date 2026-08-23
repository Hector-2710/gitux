"""Branch switch modal — lists local branches and switches on selection."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static

from gitz.git import GitError
from gitz.presenter.repo_presenter import RepoPresenter
from typing import override


class BranchScreen(ModalScreen[str]):
    """Modal listing local branches; Enter switches, Escape cancels."""

    BINDINGS: list[Binding] = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, presenter: RepoPresenter) -> None:
        super().__init__()
        self.presenter: RepoPresenter = presenter

    @override
    def compose(self) -> ComposeResult:
        """Build the modal: title, branch list, and hint line."""
        with Vertical(id="branch-modal"):
            yield Static("Switch Branch", id="branch-modal-title")
            yield OptionList(id="branch-option-list")
            yield Static("Enter: switch \u2022 Esc: cancel", id="branch-modal-hint")

    def on_mount(self) -> None:
        """Populate the branch list and focus it."""
        option_list = self.query_one("#branch-option-list", OptionList)
        branches = self.presenter.get_branches()
        for name in branches:
            _ = option_list.add_option(name)
        if not branches:
            _ = self.query_one("#branch-modal-hint", Static).update("No branches found")
        else:
            _ = option_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Switch to the selected branch and dismiss, or notify on error."""
        branch = str(event.option.prompt)
        try:
            self.presenter.switch_branch(branch)
        except GitError as exc:
            _ = self.notify(str(exc), severity="error")
            return
        _ = self.dismiss(branch)

    def action_cancel(self) -> None:
        """Dismiss the modal without selecting a branch."""
        _ = self.dismiss(None)
