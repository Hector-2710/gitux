"""Tests for gitux.ui.widgets.repo_stats_bar.RepoStatsBar."""

from unittest.mock import patch

import pytest
from textual.app import App
from textual.widgets import Static

from gitux.domain import FileCounts, HeadSummary
from gitux.ui.widgets import RepoStatsBar
from gitux.ui.widgets.repo_stats_bar import _DEFAULT_RENDER_WIDTH, _format_relative_time

T0 = 2_000_000_000

FULL_FIELDS = dict(
    user="hector",
    head_summary=HeadSummary("66f7291", "x" * 45, T0 - 172800),
    file_counts=FileCounts(1, 3, 15, 0),
    ahead=0,
    behind=0,
    remote="origin",
    remote_branch="main",
    repo_name="repo",
)


def set_fields(bar, **fields) -> None:
    """Set the private render fields on an unmounted bar."""
    for key, value in fields.items():
        setattr(bar, f"_{key}", value)


class TestRenderText:
    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_full_render_anchor(self, mock_time) -> None:
        bar = RepoStatsBar()
        set_fields(bar, steps=4, **FULL_FIELDS)
        assert bar._render_text().plain == (
            " \u25a0 \u2502 repo \u2502 hector \u2502 "
            + "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 +1 ~3 ?15 \u2502 \u21910 \u21930 \u2502 origin/main"
        )
        assert bar._render_steps().plain == "\u25cf \u25cf \u25cf \u25cf"

    def test_bare_defaults(self) -> None:
        bar = RepoStatsBar()
        assert bar._render_text().plain == (
            " \u25a0 \u2502 unknown \u2502 (no commits) "
            "\u2502 +0 ~0 ?0 \u2502 \u21910 \u21930 \u2502 (local)"
        )
        assert bar._render_steps().plain == "\u25cb \u25cb \u25cb \u25cb"

    def test_user_falls_back_to_unknown(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, user="")
        assert bar._render_text().plain.startswith(" \u25a0 \u2502 unknown \u2502")

    def test_files_segment_always_shown(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, file_counts=FileCounts(0, 0, 0, 0))
        assert "+0 ~0 ?0" in bar._render_text().plain

    def test_conflict_suffix_only_when_nonzero(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, file_counts=FileCounts(0, 0, 0, 1))
        assert " !1" in bar._render_text().plain
        bar2 = RepoStatsBar()
        set_fields(bar2, file_counts=FileCounts(0, 0, 0, 0))
        assert " !0" not in bar2._render_text().plain

    def test_remote_slug_semantics(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, remote="origin", remote_branch="main")
        assert " \u2502 origin/main" in bar._render_text().plain

        bar2 = RepoStatsBar()
        set_fields(bar2, remote="origin", remote_branch="")
        assert " \u2502 origin" in bar2._render_text().plain
        assert "origin/" not in bar2._render_text().plain

        bar3 = RepoStatsBar()
        bar3.update_stats(remote="", remote_branch="develop")
        assert bar3._remote == "(local)"
        assert bar3._remote_branch == ""
        assert "(local)" in bar3._render_text().plain

    def test_remote_capped_to_32(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, remote="r" * 40, remote_branch="")
        plain = bar._render_text().plain
        assert ("r" * 33) not in plain
        assert ("r" * 32) in plain

    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_repo_segment_first(self, mock_time) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **FULL_FIELDS)
        assert bar._render_text().plain.startswith(
            " \u25a0 \u2502 repo \u2502 "
        )

    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_repo_omitted_when_empty(self, mock_time) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **{**FULL_FIELDS, "repo_name": ""})
        assert bar._render_text().plain == (
            " \u25a0 \u2502 hector \u2502 "
            + "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 +1 ~3 ?15 \u2502 \u21910 \u21930 \u2502 origin/main"
        )
        assert bar._render_steps().plain == "\u25cb \u25cb \u25cb \u25cb"

    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_repo_capped_to_32(self, mock_time) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **{**FULL_FIELDS, "repo_name": "r" * 40})
        plain = bar._render_text().plain
        assert ("r" * 33) not in plain
        assert ("r" * 32) in plain


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

    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_subject_200_capped_to_40(self, mock_time) -> None:
        subject = "s" * 200
        bar = RepoStatsBar()
        set_fields(bar, head_summary=HeadSummary("66f7291", subject, T0))
        assert ("s" * 39 + "\u2026") in bar._render_text().plain


class TestWidthDrop:
    @pytest.fixture
    def bar(self):
        with patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0):
            bar = RepoStatsBar()
            set_fields(bar, **FULL_FIELDS)
            yield bar

    def test_width_112_full_render(self, bar) -> None:
        set_fields(bar, steps=4)
        assert bar._render_text(width=112).plain == (
            " \u25a0 \u2502 repo \u2502 hector \u2502 "
            + "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 +1 ~3 ?15 \u2502 \u21910 \u21930 \u2502 origin/main"
        )
        assert bar._render_text().plain == bar._render_text(width=112).plain
        assert bar._render_steps().plain == "\u25cf \u25cf \u25cf \u25cf"

    def test_width_111_drops_ahead(self, bar) -> None:
        plain = bar._render_text(width=111).plain
        assert "\u21910 \u21930" not in plain
        assert "origin/main" in plain
        assert " \u25cb" in bar._render_steps().plain

    def test_width_104_keeps_remote(self, bar) -> None:
        # Just above the remote window: ahead_behind dropped, remote kept
        plain = bar._render_text(width=104).plain
        assert "origin/main" in plain
        assert "\u21910 \u21930" not in plain

    @pytest.mark.parametrize("width", range(90, 104))
    def test_width_90_to_103_remote_dropped(self, bar, width) -> None:
        plain = bar._render_text(width=width).plain
        assert "origin/main" not in plain
        assert "hector" in plain

    @pytest.mark.parametrize("width", range(83, 90))
    def test_width_83_to_89_repo_dropped(self, bar, width) -> None:
        plain = bar._render_text(width=width).plain
        assert "repo" not in plain
        assert "hector" in plain

    @pytest.mark.parametrize("width", range(74, 83))
    def test_width_74_to_82_user_dropped(self, bar, width) -> None:
        plain = bar._render_text(width=width).plain
        assert "hector" not in plain
        assert "+1 ~3 ?15" in plain

    @pytest.mark.parametrize("width", range(62, 74))
    def test_width_62_to_73_files_dropped(self, bar, width) -> None:
        plain = bar._render_text(width=width).plain
        assert "+1 ~3 ?15" not in plain
        assert "2 days ago" in plain

    @pytest.mark.parametrize("width", range(49, 62))
    def test_width_49_to_61_date_dropped(self, bar, width) -> None:
        plain = bar._render_text(width=width).plain
        assert "2 days ago" not in plain
        assert ("x" * 39 + "\u2026") in plain

    def test_repo_present_at_90(self, bar) -> None:
        plain = bar._render_text(width=90).plain
        assert "repo" in plain
        assert "hector" in plain

    def test_user_present_at_83(self, bar) -> None:
        plain = bar._render_text(width=83).plain
        assert "hector" in plain

    def test_files_present_at_74(self, bar) -> None:
        plain = bar._render_text(width=74).plain
        assert "+1 ~3 ?15" in plain

    def test_date_present_at_62(self, bar) -> None:
        plain = bar._render_text(width=62).plain
        assert "2 days ago" in plain

    def test_width_48_elides_head_subject(self, bar) -> None:
        plain = bar._render_text(width=48).plain
        assert ("x" * 39 + "\u2026") not in plain
        assert "x" in plain
        assert " \u25cb" in bar._render_steps().plain

    def test_width_21_dots_present(self, bar) -> None:
        plain = bar._render_text(width=21).plain
        steps_plain = bar._render_steps().plain
        assert " \u25cf" in steps_plain or " \u25cb" in steps_plain
        assert "STATS" not in plain

    def test_boundary_inclusive(self, bar) -> None:
        set_fields(bar, steps=4)
        assert bar._render_text(width=112).plain == bar._render_text().plain
        assert "\u2191" in bar._render_text(width=112).plain

    def test_unmounted_bare_render_is_full(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **FULL_FIELDS)
        with patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0):
            plain = bar._render_text().plain
        assert _DEFAULT_RENDER_WIDTH == 200
        assert "origin/main" in plain
        assert "hector" in plain
        assert "repo" in plain
        assert " \u25cb" in bar._render_steps().plain


HS = HeadSummary("66f7291", "feat: x", T0)


class TestSteps:
    @pytest.mark.parametrize(("fields", "expected"), [
        (dict(file_counts=FileCounts(0, 0, 0, 0), head_summary=None, remote="(local)", ahead=0, behind=0), 0),
        (dict(file_counts=FileCounts(0, 0, 0, 0), head_summary=HS, remote="(local)", ahead=0, behind=0), 0),
        (dict(file_counts=FileCounts(0, 0, 0, 0), head_summary=None, remote="origin", ahead=0, behind=0), 0),
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=None, remote="origin", ahead=0, behind=0), 1),
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=None, remote="(local)", ahead=0, behind=0), 1),
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=HS, remote="(local)", ahead=0, behind=0), 2),
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=HS, remote="", ahead=0, behind=0), 2),   # row 7
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=HS, remote="(local)", ahead=0, behind=0), 2),  # row 7
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=HS, remote=None, ahead=0, behind=0), 2),  # row 7
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=HS, remote="origin", ahead=3, behind=0), 2),  # row 8/10 (diverged/no-push also 2)
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=HS, remote="origin", ahead=0, behind=2), 3),  # row 9
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=HS, remote="origin", ahead=3, behind=2), 2),  # row 10
        (dict(file_counts=FileCounts(2, 0, 0, 0), head_summary=HS, remote="origin", ahead=0, behind=0), 4),  # row 11
        (dict(file_counts=FileCounts(0, 0, 0, 3), head_summary=HS, remote="origin", ahead=0, behind=0), 0),  # row 12
    ])
    def test_step_truth_table(self, fields, expected) -> None:
        bar = RepoStatsBar()
        bar.update_stats(**fields)
        assert bar._steps == expected

    def test_file_counts_none_step1_false(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats()
        assert bar._steps == 0

    def test_steps_override(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats(
            file_counts=FileCounts(0, 0, 0, 0),
            head_summary=None,
            remote="(local)",
            ahead=0,
            behind=0,
            steps=2,
        )
        assert bar._steps == 2

    @pytest.mark.parametrize("steps", [0, 1, 2, 3, 4])
    def test_dot_counts(self, steps) -> None:
        bar = RepoStatsBar()
        set_fields(bar, steps=steps, **FULL_FIELDS)
        steps_plain = bar._render_steps().plain
        assert steps_plain.count("\u25cf") == steps
        assert steps_plain.count("\u25cb") == 4 - steps

    def test_steps_override_renders(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats(
            file_counts=FileCounts(0, 0, 0, 0),
            head_summary=None,
            remote="(local)",
            ahead=0,
            behind=0,
            steps=2,
        )
        steps_plain = bar._render_steps().plain
        assert steps_plain.count("\u25cf") == 2
        assert steps_plain.count("\u25cb") == 2
        bar2 = RepoStatsBar()
        set_fields(bar2, steps=4, **FULL_FIELDS)
        steps_plain2 = bar2._render_steps().plain
        assert steps_plain2.count("\u25cf") == 4
        assert steps_plain2.count("\u25cb") == 0


class TestNoCommits:
    def test_head_slot_no_commits_and_date_omitted(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, user="hector", head_summary=None)
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
                    user="hector",
                    head_summary=HeadSummary("66f7291", "x" * 45, T0 - 172800),
                    file_counts=FileCounts(1, 3, 15, 0),
                    remote="origin",
                    remote_branch="main",
                )
            left = bar.query_one("#stats-left", Static)
            assert left.content.plain.startswith(
                " \u25a0 \u2502 hector \u2502 "
            )

    # AC-28: remote normalization ("(local)") and remote/branch slug are
    # covered by the two tests below (remote="" / remote="(local)" and
    # remote="origin", remote_branch="main").

    def test_update_stats_no_remote_falls_back_to_local(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats(remote="", remote_branch="develop")
        assert bar._remote == "(local)"
        assert bar._remote_branch == ""
        assert "(local)" in bar._render_text().plain

    def test_update_stats_remote_with_branch(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats(remote="origin", remote_branch="main")
        assert "origin/main" in bar._render_text().plain

    def test_update_stats_defaults_file_counts(self) -> None:
        bar = RepoStatsBar()
        bar.update_stats()
        assert bar._file_counts is None
        assert "+0 ~0 ?0" in bar._render_text().plain


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
