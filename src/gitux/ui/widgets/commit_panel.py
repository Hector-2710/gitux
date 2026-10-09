"""Commit panel — the permanent bottom panel (skeleton K1, scope S5).

Replaces the commit modal: always visible at the bottom of the board, the
user writes the message without losing sight of the files. One wrapping
editor (``soft_wrap``): the first line is the subject, the rest is the
body — git's own convention. ``c`` focuses it, ``Esc`` returns focus to
the board, ``Ctrl+Enter`` commits. Shows branch + push target and the
subject char count; a compact affordance line is part of the element (D10).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static, TextArea

_MAX_MESSAGE_CHARS = 400
"""Hard cap on the commit message (owner decision, 2026-10-01)."""

_MAX_SUBJECT_CHARS = 72


class CommitPanel(Vertical):
    """Permanent commit panel: one wrapping editor, one keystroke away.

    Behaves as a board block (K8): Tab cycles into it, it illuminates with
    the active border like the files/diff blocks, and it holds the keyboard
    while active.
    """

    DEFAULT_CLASSES = "block-inactive"

    BINDINGS: list[Binding] = [
        Binding("ctrl+enter", "commit", "Commit", show=False),
        Binding("escape", "back", "Back", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._branch: str = ""
        self._target: str = ""

    def compose(self) -> ComposeResult:
        """Build the panel: context line, message editor, affordance."""
        yield Static("", id="commit-context")
        yield TextArea(
            "",
            id="commit-message",
            soft_wrap=True,
            show_line_numbers=False,
            highlight_cursor_line=False,
            placeholder="commit message",
        )
        yield Static("", id="commit-affordance")

    def on_mount(self) -> None:
        """Render the initial context and affordance lines."""
        self._render_context()
        self._render_affordance()

    # ── Context + affordance rendering ──────────────────────────────────

    def update_context(self, branch: str, target: str) -> None:
        """Show the commit destination: current branch → push target (K1)."""
        self._branch = branch
        self._target = target
        self._render_context()

    def _render_context(self) -> None:
        line = f"COMMIT \u2014 {self._branch or '…'}"
        if self._target:
            line = f"{line} \u2192 {self._target}"
        self.query_one("#commit-context", Static).update(line)

    def _render_affordance(self) -> None:
        """Affordance line: subject char count + the panel's own keys."""
        subject = self._subject()
        count = len(subject)
        marker = " \u2022 over 72" if count > _MAX_SUBJECT_CHARS else ""
        self.query_one("#commit-affordance", Static).update(
            f"{len(self._editor().text)}/{_MAX_MESSAGE_CHARS} chars{marker}"
            f" \u00b7 Ctrl+Enter commit \u00b7 Esc back"
        )

    def on_text_area_changed(self, _event: TextArea.Changed) -> None:
        """Enforce the 400-char cap and re-render the char count."""
        editor = self._editor()
        if len(editor.text) > _MAX_MESSAGE_CHARS:
            editor.text = editor.text[:_MAX_MESSAGE_CHARS]
        self._render_affordance()

    # ── Block behavior (K8: the panel is a board block) ────────────────

    def set_active(self, active: bool) -> None:
        """Toggle the active state — same treatment as the files/diff blocks."""
        _ = self.set_class(active, "block-active")
        _ = self.set_class(not active, "block-inactive")

    # ── Message parsing (git convention: line 1 = subject, rest = body) ─

    def _editor(self) -> TextArea:
        return self.query_one("#commit-message", TextArea)

    def _subject(self) -> str:
        text = self._editor().text
        lines = text.splitlines()
        return lines[0] if lines else ""

    def _body(self) -> str:
        text = self._editor().text
        lines = text.splitlines()
        return "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

    # ── Focus + clearing ───────────────────────────────────────────────

    def focus_message(self) -> None:
        """Focus the message editor (the board's ``c`` action lands here)."""
        self._editor().focus()

    def clear_inputs(self) -> None:
        """Clear the message after a successful commit."""
        self._editor().text = ""
        self._render_affordance()

    def has_keyboard(self) -> bool:  # noqa: D401 - convenience predicate
        """True while the message editor holds focus."""
        focused = self.screen.focused if self.screen else None
        return focused is not None and focused is self._editor()

    # ── Actions ────────────────────────────────────────────────────────

    def action_commit(self) -> None:
        """Send subject + body to the app's commit flow (Ctrl+Enter)."""
        self.app.commit_from_panel(self._subject(), self._body())

    def action_back(self) -> None:
        """Return focus to the board (Esc)."""
        self.app.return_focus_to_board()
