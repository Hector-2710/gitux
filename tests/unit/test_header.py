"""Tests for gitux.ui.widgets.header.TopAppBar render contract."""

from unittest.mock import patch

from gitux.domain import WipState
from gitux.ui.widgets.header import (
    _MAX_BRANCH_CHARS,
    _MAX_OWNER_CHARS,
    _MAX_REPO_CHARS,
    _WIP_DOT_STYLE,
)
from gitux.ui.widgets.header import TopAppBar


class TestRenderText:
    def test_full_render_with_star(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._owner = "Hector-2710"
        bar._branch = "main"
        bar._default_branch = "main"
        bar._wip_state = WipState.CLEAN
        assert bar._render_text().plain == " \u25c9 GITUX // Hector-2710/gitux [main*] \u25cf  \u2699"

    def test_no_owner(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._branch = "main"
        bar._wip_state = WipState.UNKNOWN
        assert bar._render_text().plain == " \u25c9 GITUX // gitux [main] \u25cf  \u2699"

    def test_not_default_branch_no_star(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._owner = "Hector-2710"
        bar._branch = "feature/x"
        bar._default_branch = "main"
        assert bar._render_text().plain == " \u25c9 GITUX // Hector-2710/gitux [feature/x] \u25cf  \u2699"

    def test_detached_empty_branch_no_badge(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._owner = "Hector-2710"
        bar._branch = ""
        bar._is_detached = True
        assert bar._render_text().plain == " \u25c9 GITUX // Hector-2710/gitux \u25cf  \u2699"

    def test_empty_repo(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._branch = "main"
        bar._wip_state = WipState.UNKNOWN
        assert bar._render_text().plain == " \u25c9 GITUX // gitux [main] \u25cf  \u2699"

    def test_star_absent_when_no_default(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._branch = "main"
        bar._default_branch = ""
        assert "[main]" in bar._render_text().plain
        assert "[main*]" not in bar._render_text().plain


class TestOwnerCaps:
    def test_owner_truncated_to_24(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._owner = "o" * 30
        bar._branch = ""
        plain = bar._render_text().plain
        assert plain == f" \u25c9 GITUX // {'o' * _MAX_OWNER_CHARS}/gitux \u25cf  \u2699"

    def test_repo_truncated_to_32(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "r" * 40
        bar._branch = ""
        assert f" {'r' * _MAX_REPO_CHARS} \u25cf" in bar._render_text().plain

    def test_branch_truncated_to_24(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._branch = "b" * 30
        bar._default_branch = "b" * 30
        assert f"[{'b' * _MAX_BRANCH_CHARS}*]" in bar._render_text().plain


class TestWipDot:
    def test_span_style_per_state(self) -> None:
        for state in WipState:
            bar = TopAppBar()
            bar._repo_name = "gitux"
            bar._branch = ""
            bar._wip_state = state
            text = bar._render_text()
            assert any(
                span.style == _WIP_DOT_STYLE[state]
                and text.plain[span.start : span.end] == " \u25cf"
                for span in text.spans
            )

    def test_plain_identical_across_states(self) -> None:
        plains = []
        for state in WipState:
            bar = TopAppBar()
            bar._repo_name = "gitux"
            bar._branch = ""
            bar._wip_state = state
            plains.append(bar._render_text().plain)
        assert len(set(plains)) == 1


class TestUpdateDisplay:
    def test_gear_suffix_and_leading_space(self) -> None:
        bar = TopAppBar()
        bar._repo_name = "gitux"
        bar._branch = ""
        plain = bar._render_text().plain
        assert plain.startswith(" ")
        assert plain.endswith("  \u2699")

    def test_update_display_stores_fields(self) -> None:
        bar = TopAppBar()
        with patch.object(bar, "update"):
            bar.update_display(
                repo_name="gitux",
                owner="Hector-2710",
                branch="main",
                is_detached=False,
                default_branch="main",
                wip_state=WipState.DIRTY,
            )
        assert bar._owner == "Hector-2710"
        assert bar._default_branch == "main"
        assert bar._wip_state == WipState.DIRTY

    def test_update_display_empty_repo_fallback(self) -> None:
        bar = TopAppBar()
        with patch.object(bar, "update"):
            bar.update_display(repo_name="", branch="")
        assert bar._repo_name == "..."
