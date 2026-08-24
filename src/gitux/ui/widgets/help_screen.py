"""Help screen modal — shows all keyboard shortcuts."""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


class HelpScreen(ModalScreen[None]):
    """Modal screen displaying all keyboard shortcuts."""

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
            t.append(f"\n  {title}\n", style="bold #6366f1")

        def _shortcut(key: str, desc: str) -> None:
            """Append a shortcut row line."""
            t.append(f"    {key:<14}", style="bold #f59e0b")
            t.append(f"{desc}\n", style="#e2e8f0")

        # ── Navigation ──
        _section("Navigation")
        _shortcut("Tab", "Next section (Files/Commits/Diff)")
        _shortcut("\u2191 / \u2193", "Scroll active section content")
        _shortcut("Enter", "Activate selected section")
        _shortcut("j / k", "Scroll down / up")

        # ── File Actions ──
        _section("Files")
        _shortcut("s / Enter", "Stage / Unstage file")
        _shortcut("a", "Stage all files")
        _shortcut("A", "Unstage all files")

        # ── Commit & Push ──
        _section("Commit & Push")
        _shortcut("c", "Focus commit message")
        _shortcut("Ctrl+Enter", "Create commit")
        _shortcut("Ctrl+p", "Push to remote")

        # ── General ──
        _section("General")
        _shortcut("r", "Refresh status")
        _shortcut("b", "Branches panel")
        _shortcut("?", "Show this help")
        _shortcut("q", "Quit GITUX")
        _shortcut("Escape", "Cancel / Go back")

        # ── Upcoming (dimmed) ──
        _section("Coming Soon")
        t.append("    /              Search files\n", style="dim #64748b")
        t.append("    L              Commit log\n", style="dim #64748b")
        t.append("    S              Stash panel\n", style="dim #64748b")

        return t
