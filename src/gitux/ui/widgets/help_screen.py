"""Help screen modal — the only guidance surface (skeleton K5, structure T5).

Lists the REAL key set, grouped by screen (board / commit block / branches
/ log), plus the step-dots legend. No phantom actions (V7): every key here
exists in the app. Colors use the V1 tokens.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from gitux.ui import tokens

_SECTION_STYLE = f"bold {tokens.PURPLE_EMPHASIS}"
_KEY_STYLE = f"bold {tokens.AMBER}"
_DESC_STYLE = tokens.TEXT_SECONDARY
_LEGEND_STYLE = tokens.TEXT_DIM


class HelpScreen(ModalScreen[None]):
    """Modal screen displaying the real keyboard shortcuts (K5)."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("?", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Build the modal: title, help body, and close hint."""
        with Vertical(id="help-container"):
            yield Static("GITUX — Keyboard Shortcuts", id="help-title")
            yield Static(self._build_help_text(), id="help-body")
            yield Static("Press ? or Esc to close", id="help-close-hint")

    @staticmethod
    def _build_help_text() -> Text:
        """Build the keyboard-shortcut reference as rich text."""
        t = Text()

        def _section(title: str) -> None:
            """Append a section header line."""
            t.append(f"\n  {title}\n", style=_SECTION_STYLE)

        def _shortcut(key: str, desc: str) -> None:
            """Append a shortcut row line."""
            t.append(f"    {key:<14}", style=_KEY_STYLE)
            t.append(f"{desc}\n", style=_DESC_STYLE)

        # ── Board ──
        _section("Board")
        _shortcut("Tab", "Next block (files / diff / commit)")
        _shortcut("\u2191/\u2193 or j/k", "Move in the active block")
        _shortcut("s / Enter", "Stage / unstage file")
        _shortcut("a / A", "Stage all / unstage all")
        _shortcut("p", "Pull from remote")
        _shortcut("Ctrl+p", "Push to remote")
        _shortcut("b", "Branches screen")
        _shortcut("l", "Commit log")
        _shortcut("?", "Show this help")
        _shortcut("q", "Quit GITUX")

        # ── Commit block ──
        _section("Commit block")
        _shortcut("Ctrl+Enter", "Create commit")
        _shortcut("Enter", "New line (message body)")
        _shortcut("Esc", "Back to the files block")

        # ── Branches screen ──
        _section("Branches screen")
        _shortcut("Enter", "Switch to branch")
        _shortcut("m", "Merge into current branch")
        _shortcut("d", "Delete branch (y confirms)")
        _shortcut("n", "New branch (type name, Enter)")
        _shortcut("Esc", "Cancel")

        # ── Log screen ──
        _section("Log screen")
        _shortcut("\u2191/\u2193", "Navigate commits")
        _shortcut("Enter", "Commit details")
        _shortcut("Esc", "Close")

        # ── Step-dots legend (K5) ──
        _section("Steps")
        t.append(
            "    \u25cf  staged \u2192 commit \u2192 push \u2192 pull\n",
            style=_LEGEND_STYLE,
        )
        t.append(
            "       (no dots lit = fully synced)\n",
            style=_LEGEND_STYLE,
        )

        return t
