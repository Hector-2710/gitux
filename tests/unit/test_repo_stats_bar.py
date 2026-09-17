"""Tests for gitux.ui.widgets.repo_stats_bar.RepoStatsBar."""

from unittest.mock import patch

import pytest
from textual.app import App
from textual.widgets import Static

from gitux.domain import HeadSummary
from gitux.ui.widgets import RepoStatsBar
from gitux.ui.widgets.repo_stats_bar import _DEFAULT_RENDER_WIDTH, _format_relative_time

T0 = 2_000_000_000

FULL_FIELDS = dict(
    repo_name="repo",
    branch="main",
    head_summary=HeadSummary("66f7291", "x" * 45, T0 - 172800),
)


def set_fields(bar, **fields) -> None:
    """Set the private render fields on an unmounted bar."""
    for key, value in fields.items():
        setattr(bar, f"_{key}", value)


class TestRenderText:
    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_full_render_anchor(self, mock_time) -> None:
        bar = RepoStatsBar()
        set_fields(bar, steps=3, **FULL_FIELDS)
        assert bar._render_text().plain == (
            "repo \u2502 "
            + "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 main"
        )
        assert bar._render_steps().plain == "\u25cf  \u25cf  \u25cf"

    def test_bare_defaults(self) -> None:
        bar = RepoStatsBar()
        assert bar._render_text().plain == "(no commits)"
        assert bar._render_steps().plain == "\u25cb  \u25cb  \u25cb"

    def test_no_leading_icon(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **FULL_FIELDS)
        assert not bar._render_text().plain.startswith(" \u25a0")

    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_repo_omitted_when_empty(self, mock_time) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **{**FULL_FIELDS, "repo_name": ""})
        assert bar._render_text().plain == (
            "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 main"
        )

    def test_branch_omitted_when_empty(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **{**FULL_FIELDS, "branch": ""})
        assert "main" not in bar._render_text().plain

    def test_repo_capped_to_32(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **{**FULL_FIELDS, "repo_name": "r" * 40})
        plain = bar._render_text().plain
        assert ("r" * 33) not in plain
        assert ("r" * 32) in plain

    def test_branch_capped_to_24(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **{**FULL_FIELDS, "branch": "b" * 40})
        plain = bar._render_text().plain
        assert ("b" * 25) not in plain
        assert ("b" * 24) in plain


class TestSubjectCap:
    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_subject_exactly_40_unchanged(self, mock_time) -> None:
        subject = "s" * 40
        bar = RepoStatsBar()
        set_fields(bar, head_summary=HeadSummary("66f7291", subject, T0))
        assert ("s" * 40) in bar._render_text().plain

    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_subject_41_truncated(self, mock_time) -> None:
        subject = "s" * 41
        bar = RepoStatsBar()
        set_fields(bar, head_summary=HeadSummary("66f7291", subject, T0))
        plain = bar._render_text().plain
        assert ("s" * 39 + "\u2026") in plain
        assert "ssssssssssssssssssssssssssssssssssssssss" not in plain


class TestWidthDrop:
    @pytest.fixture
    def bar(self):
        with patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0):
            bar = RepoStatsBar()
            set_fields(bar, **FULL_FIELDS)
            yield bar

    def test_width_112_full_render(self, bar) -> None:
        set_fields(bar, steps=3)
        assert bar._render_text(width=112).plain == (
            "repo \u2502 "
            + "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 main"
        )
        assert bar._render_text().plain == bar._render_text(width=112).plain
        assert bar._render_steps().plain == "\u25cf  \u25cf  \u25cf"

    def test_width_72_drops_branch(self, bar) -> None:
        plain = bar._render_text(width=72).plain
        assert "main" not in plain
        assert "repo" in plain
        assert " \u25cb" in bar._render_steps().plain

    def test_width_65_drops_repo(self, bar) -> None:
        plain = bar._render_text(width=65).plain
        assert "repo" not in plain
        assert "2 days ago" in plain

    def test_width_58_drops_date(self, bar) -> None:
        plain = bar._render_text(width=58).plain
        assert "2 days ago" not in plain
        assert ("x" * 39 + "\u2026") in plain

    def test_width_45_elides_head_subject(self, bar) -> None:
        plain = bar._render_text(width=45).plain
        assert ("x" * 40) not in plain  # subject truncated, not full 40 chars
        assert "x" in plain
        assert " \u25cb" in bar._render_steps().plain

    def test_width_18_dots_present(self, bar) -> None:
        plain = bar._render_text(width=18).plain
        steps_plain = bar._render_steps().plain
        assert " \u25cf" in steps_plain or " \u25cb" in steps_plain
        assert "STATS" not in plain

    def test_unmounted_bare_render_is_full(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **FULL_FIELDS)
        with patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0):
            plain = bar._render_text().plain
        assert _DEFAULT_RENDER_WIDTH == 200
        assert "main" in plain
        assert "repo" in plain
        assert " \u25cb" in bar._render_steps().plain


class TestSteps:
    def test_steps_override(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats(steps=2)
        assert bar._steps == 2

    @pytest.mark.parametrize("steps", [0, 1, 2, 3])
    def test_dot_counts(self, steps) -> None:
        bar = RepoStatsBar()
        set_fields(bar, steps=steps, **FULL_FIELDS)
        steps_plain = bar._render_steps().plain
        assert steps_plain.count("\u25cf") == steps
        assert steps_plain.count("\u25cb") == 3 - steps

    def test_steps_override_renders(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats(steps=2)
        steps_plain = bar._render_steps().plain
        assert steps_plain.count("\u25cf") == 2
        assert steps_plain.count("\u25cb") == 1
        bar2 = RepoStatsBar()
        set_fields(bar2, steps=3, **FULL_FIELDS)
        steps_plain2 = bar2._render_steps().plain
        assert steps_plain2.count("\u25cf") == 3
        assert steps_plain2.count("\u25cb") == 0


class TestNoCommits:
    def test_head_slot_no_commits_and_date_omitted(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, repo_name="repo", branch="main", head_summary=None)
        plain = bar._render_text().plain
        assert "(no commits)" in plain
        assert "ago" not in plain


class TestUpdateStats:
    @pytest.mark.asyncio
    async def test_update_stats_inside_running_app(self) -> None:
        app = App()
        async with app.run_test():
            bar = RepoStatsBar(id="stats-bar")
            await app.mount(bar)
            with patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0):
                bar.update_stats(
                    repo_name="repo",
                    branch="main",
                    head_summary=HeadSummary("66f7291", "x" * 45, T0 - 172800),
                )
            left = bar.query_one("#stats-left", Static)
            assert left.content.plain.startswith(
                "repo \u2502 "
            )

    def test_update_stats_defaults(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats()
        assert bar._repo_name == ""
        assert bar._branch == ""
        assert bar._head_summary is None
        assert bar._render_text().plain == "(no commits)"


class TestFormatRelativeTime:
    @pytest.mark.parametrize(
        ("delta", "expected"),
        [
            (0, "just now"),
            (30, "just now"),
            (60, "1 minute ago"),
            (89, "1 minute ago"),
            (90, "1 minutes ago"),
            (2699, "44 minutes ago"),
            (2700, "1 hour ago"),
            (5399, "1 hour ago"),
            (5400, "1 hours ago"),
            (86399, "23 hours ago"),
            (86400, "1 day ago"),
            (129599, "1 day ago"),
            (129600, "1 days ago"),
            (604799, "6 days ago"),
            (604800, "1 weeks ago"),
            (2591999, "4 weeks ago"),
            (2592000, "1 months ago"),
            (31536000, "1 years ago"),
        ],
    )
    def test_boundary_table(self, delta, expected) -> None:
        assert _format_relative_time(T0 - delta, now=T0) == expected

    def test_future_epoch_clamps_to_just_now(self) -> None:
        assert _format_relative_time(T0 + 300, now=T0) == "just now"
