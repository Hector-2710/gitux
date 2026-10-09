"""Tests for the help screen (skeleton K5 / surface V7).

The help is the ONLY guidance surface (T5) — it must list the real key set
and no phantom actions.
"""

from gitux.ui.app import GituxApp
from gitux.ui.widgets.help_screen import HelpScreen


def _help_text() -> str:
    return HelpScreen._build_help_text().plain


def test_help_groups_by_screen():
    """K5: keys grouped by screen — board, commit block, branches, log."""
    text = _help_text()
    for section in ("Board", "Commit block", "Branches screen", "Log screen"):
        assert section in text


def test_help_documents_three_block_tab():
    """K8 (amended): Tab cycles files / diff / commit."""
    text = _help_text()
    tab_line = next(line for line in text.splitlines() if line.strip().startswith("Tab"))
    assert "files / diff / commit" in tab_line


def test_help_has_steps_legend():
    """K5: the step-dots legend ships with the help."""
    text = _help_text()
    assert "Steps" in text
    assert "staged \u2192 commit \u2192 push \u2192 pull" in text
    assert "synced" in text


def test_help_lists_no_phantom_actions():
    """V7: no stash, no search, no manual refresh, no ``c``."""
    text = _help_text()
    low = text.lower()
    assert "stash" not in low
    assert "search" not in low
    assert "refresh" not in low
    assert "Coming Soon" not in text
    # ``c`` is gone from the interaction model (K8 amendment)
    commit_lines = [l for l in text.splitlines() if "commit" in l.lower()]
    assert all(not l.strip().startswith("c ") for l in commit_lines)


def test_help_board_keys_exist_in_app():
    """Consistency: every board key the help claims is real."""
    binding_keys = {binding.key for binding in GituxApp.BINDINGS}
    for key in ("p", "ctrl+p", "b", "l", "question_mark", "q"):
        assert key in binding_keys, f"help claims {key!r} but it is not bound"
    # Tab cycles via the focus_next override (K8)
    assert getattr(GituxApp, "action_focus_next", None) is not None


def test_help_branches_actions_match_screen():
    """K3: the branches screen's m/d/n model is documented."""
    text = _help_text()
    for fragment in ("Merge into current", "Delete branch (y confirms)", "New branch"):
        assert fragment in text
