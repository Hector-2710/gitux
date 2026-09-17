"""Top application bar — displays repo name, owner, branch badge, and WIP state."""

from rich.text import Text
from textual.widgets import Static

from gitux.domain import WipState

_MAX_OWNER_CHARS: int = 24
_MAX_REPO_CHARS: int = 32
_MAX_BRANCH_CHARS: int = 24

_WIP_DOT_STYLE: dict[WipState, str] = {
    WipState.CLEAN: "#10b981",    # green
    WipState.DIRTY: "#ffb783",    # yellow
    WipState.CONFLICT: "#ffb4ab",  # red
    WipState.UNKNOWN: "#908fa0",   # gray
}


class TopAppBar(Static):
    """Header bar showing repository identity and current branch.

    Renders a compact one-line header with:
    - Circled dot icon + "GITUX //" prefix
    - Owner/repo name
    - Branch name in a styled badge (with ``*`` on the default branch), or
      detached-HEAD warning in red
    - Work-in-progress dot
    - Gear icon suffix
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._repo_name: str = ""
        self._owner: str = ""
        self._branch: str = ""
        self._is_detached: bool = False
        self._default_branch: str = ""
        self._wip_state: WipState = WipState.UNKNOWN

    def update_display(
        self,
        repo_name: str = "",
        owner: str = "",
        branch: str = "",
        is_detached: bool = False,
        default_branch: str = "",
        wip_state: WipState = WipState.UNKNOWN,
    ) -> None:
        """Update the header with current repo and branch information."""
        self._repo_name = repo_name or "..."
        self._owner = owner
        self._branch = branch
        self._is_detached = is_detached
        self._default_branch = default_branch
        self._wip_state = wip_state
        self.update(self._render_text())

    def _render_text(self) -> Text:
        """Render the header line as rich text."""
        text = Text()
        text.append(" \u25c9", style="bold #9c60ec")
        text.append(" GITUX // ", style="#e4e1ed")
        repo = self._repo_name[:_MAX_REPO_CHARS]
        if self._owner:
            text.append(
                f"{self._owner[:_MAX_OWNER_CHARS]}/{repo}", style="#e4e1ed"
            )
        else:
            text.append(repo, style="#e4e1ed")
        if self._branch:
            branch = self._branch[:_MAX_BRANCH_CHARS]
            star = "*" if self._branch == self._default_branch else ""
            if self._is_detached:
                text.append(f" ({branch})", style="#ffb4ab on #93000a")
            else:
                text.append(f" [{branch}{star}]", style="#221d2f on #d19dfb")
        text.append(" \u25cf", style=_WIP_DOT_STYLE[self._wip_state])
        text.append("  ", style="")
        text.append("\u2699", style="#c7c4d7")
        return text
