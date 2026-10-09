"""Branch screen — switch, merge, delete, create (skeleton K3, scope S2).

Modal listing local branches with the current one marked. On the selected
branch: ``Enter`` switch · ``m`` merge into current · ``d`` delete (asks for
confirmation — the prevention rung, T3) · ``n`` new branch (name input).
``Esc`` cancels. Errors route to the app's error line with the next action
named (structure T3); success dismisses with a message the app displays.
"""

from typing import override

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from gitux.git import GitError
from gitux.presenter.repo_presenter import RepoPresenter

_LIST_HINT = "Enter switch \u2022 m merge \u2022 d delete \u2022 n new \u2022 Esc cancel"


class BranchScreen(ModalScreen[str]):
    """Branch action modal: switch / merge / delete / create (K3)."""

    BINDINGS: list[Binding] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("m", "merge", "Merge", show=False),
        Binding("d", "delete", "Delete", show=False),
        Binding("n", "new", "New", show=False),
        Binding("y", "confirm_delete", "Confirm", show=False),
    ]

    def __init__(self, presenter: RepoPresenter) -> None:
        super().__init__()
        self.presenter: RepoPresenter = presenter
        self._current: str = ""
        self._confirming_delete: bool = False

    @override
    def compose(self) -> ComposeResult:
        """Build the modal: title, branch list, name input, hint line."""
        with Vertical(id="branch-modal"):
            yield Static("Branches", id="branch-modal-title")
            yield OptionList(id="branch-option-list")
            yield Input(placeholder="new branch name…", id="branch-name-input")
            yield Static(_LIST_HINT, id="branch-modal-hint")

    @override
    def on_mount(self) -> None:
        """Populate the branch list, mark the current one, hide the input."""
        option_list = self.query_one("#branch-option-list", OptionList)
        name_input = self.query_one("#branch-name-input", Input)
        name_input.display = False
        try:
            branches = self.presenter.get_branches()
            self._current = self.presenter.get_current_branch()
        except GitError as exc:
            self.app.show_error(
                f"could not list branches: {exc} \u2192 check the repository, then b again"
            )
            branches, self._current = [], ""
        for name in branches:
            marker = "\u25cf " if name == self._current else "  "
            option_list.add_option(Option(f"{marker}{name}", id=name))
        if not branches:
            self.query_one("#branch-modal-hint", Static).update("No branches found")
        else:
            option_list.focus()

    # ── Helpers ─────────────────────────────────────────────────────────

    def _selected_branch(self) -> str | None:
        """Return the selected branch name (option id), or None."""
        option_list = self.query_one("#branch-option-list", OptionList)
        highlighted = option_list.highlighted
        if highlighted is None:
            return None
        option = option_list.get_option_at_index(highlighted)
        return str(option.id) if option and option.id else None

    def _set_hint(self, text: str) -> None:
        self.query_one("#branch-modal-hint", Static).update(text)

    def _reset_hint(self) -> None:
        self._confirming_delete = False
        self._set_hint(_LIST_HINT)

    # ── Actions ─────────────────────────────────────────────────────────

    def action_cancel(self) -> None:
        """Dismiss the modal without doing anything."""
        _ = self.dismiss(None)

    def action_merge(self) -> None:
        """Merge the selected branch into the current one (``m``)."""
        if self._name_input_visible():
            return  # typing a branch name — keys belong to the input
        branch = self._selected_branch()
        if branch is None:
            return
        if branch == self._current:
            self._set_hint(f"already on {branch} \u2014 select another branch to merge")
            self.set_timer(2.0, self._reset_hint)
            return
        try:
            self.presenter.merge_branch(branch)
        except GitError as exc:
            self.app.show_error(
                f"merge failed: {exc} \u2192 resolve conflicts in your editor, then c to commit"
            )
            return
        _ = self.dismiss(f"Merged {branch} into {self._current}")

    def action_delete(self) -> None:
        """Ask for confirmation before deleting (prevention rung, T3)."""
        if self._name_input_visible():
            return
        branch = self._selected_branch()
        if branch is None:
            return
        if branch == self._current:
            self._set_hint(f"cannot delete {branch} \u2014 it is the current branch")
            self.set_timer(2.0, self._reset_hint)
            return
        self._confirming_delete = True
        self._set_hint(f"Delete '{branch}'? press y to confirm \u2022 any other key cancels")

    def action_confirm_delete(self) -> None:
        """Delete the branch after ``y`` confirms (safe -d at the git level)."""
        if not self._confirming_delete:
            return
        branch = self._selected_branch()
        self._reset_hint()
        if branch is None:
            return
        try:
            self.presenter.delete_branch(branch)
        except GitError as exc:
            self.app.show_error(
                f"delete failed: {exc} \u2192 unmerged branches need -D outside gitux, then b again"
            )
            return
        _ = self.dismiss(f"Deleted {branch}")

    def action_new(self) -> None:
        """Show the name input to create a branch (``n``)."""
        if self._name_input_visible():
            return
        name_input = self.query_one("#branch-name-input", Input)
        name_input.display = True
        name_input.value = ""
        self._set_hint("type a name \u2022 Enter creates \u2022 Esc cancels")
        name_input.focus()

    def _name_input_visible(self) -> bool:
        return self.query_one("#branch-name-input", Input).display

    # ── Events ──────────────────────────────────────────────────────────

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Enter in the name input creates the branch."""
        name_input = self.query_one("#branch-name-input", Input)
        name = name_input.value.strip()
        if not name:
            return
        try:
            self.presenter.create_branch(name)
        except GitError as exc:
            self.app.show_error(
                f"create failed: {exc} \u2192 check the name, then n again"
            )
            return
        _ = self.dismiss(f"Created {name}")

    @override
    def on_key(self, event) -> None:  # noqa: ANN001 — textual Key event
        """Cancel the delete confirmation on any non-y key."""
        if self._confirming_delete and event.key != "y":
            event.stop()
            event.prevent_default()
            self._reset_hint()
        # Esc while naming: hide the input, stay on the list
        elif self._name_input_visible() and event.key == "escape":
            event.stop()
            event.prevent_default()
            name_input = self.query_one("#branch-name-input", Input)
            name_input.display = False
            name_input.value = ""
            self._reset_hint()
            self.query_one("#branch-option-list", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Switch to the selected branch (``Enter``)."""
        branch_id = getattr(event.option, "id", None)
        branch = str(branch_id) if branch_id else str(event.option.prompt)
        try:
            self.presenter.switch_branch(branch)
        except GitError as exc:
            self.app.show_error(
                f"branch switch failed: {exc} \u2192 commit your changes first (c), then b again"
            )
            return
        _ = self.dismiss(f"Switched to {branch}")
