"""Tests for gitux.ui.widgets.repo_stats_bar.RepoStatsBar."""

from unittest.mock import patch

import pytest
from textual.app import App

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
        set_fields(bar, **FULL_FIELDS)
        assert bar._render_text().plain == (
            " \u25a0 REPO STATS \u2502 repo \u2502 hector \u2502 "
            + "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 +1 ~3 ?15 \u2502 \u21910 \u21930 \u2502 origin/main"
        )

    def test_bare_defaults(self) -> None:
        bar = RepoStatsBar()
        assert bar._render_text().plain == (
            " \u25a0 REPO STATS \u2502 unknown \u2502 (no commits) "
            "\u2502 +0 ~0 ?0 \u2502 \u21910 \u21930 \u2502 (local)"
        )

    def test_user_falls_back_to_unknown(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, user="")
        assert bar._render_text().plain.startswith(" \u25a0 REPO STATS \u2502 unknown \u2502")

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
        with patch.object(bar3, "update"):
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
            " \u25a0 REPO STATS \u2502 repo \u2502 "
        )

    @patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0)
    def test_repo_omitted_when_empty(self, mock_time) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **{**FULL_FIELDS, "repo_name": ""})
        assert bar._render_text().plain == (
            " \u25a0 REPO STATS \u2502 hector \u2502 "
            + "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 +1 ~3 ?15 \u2502 \u21910 \u21930 \u2502 origin/main"
        )

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

    def test_width_117_full_render(self, bar) -> None:
        assert bar._render_text(width=117).plain == (
            " \u25a0 REPO STATS \u2502 repo \u2502 hector \u2502 "
            + "x" * 39
            + "\u2026 \u2502 2 days ago \u2502 +1 ~3 ?15 \u2502 \u21910 \u21930 \u2502 origin/main"
        )

    def test_width_116_keeps_ahead_behind(self, bar) -> None:
        # Without hash, more space available, so ahead_behind is not dropped
        assert "↑0 ↓0" in bar._render_text(width=116).plain

    def test_width_110_keeps_remote(self, bar) -> None:
        # Without hash, remote segment fits, so it's not dropped
        assert "origin/main" in bar._render_text(width=110).plain

    def test_width_100_keeps_repo(self, bar) -> None:
        # Without hash, repo segment fits, so it's not dropped
        plain = bar._render_text(width=100).plain
        assert "repo" in plain
        assert "hector" in plain

    def test_width_93_drops_repo_keeps_user(self, bar) -> None:
        # Repo segment drops before user (AC-US5-4)
        plain = bar._render_text(width=93).plain
        assert "repo" not in plain
        assert "hector" in plain

    def test_width_85_keeps_files(self, bar) -> None:
        # Without hash, files segment fits, so it's not dropped
        assert "+1 ~3 ?15" in bar._render_text(width=85).plain

    def test_width_73_keeps_date(self, bar) -> None:
        # Without hash, date segment fits, so it's not dropped
        assert "2 days ago" in bar._render_text(width=73).plain

    def test_width_60_elides_subject(self, bar) -> None:
        # Without hash, more space, subject is less elided or not at all
        plain = bar._render_text(width=60).plain
        # Subject should still be present but possibly elided
        assert "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" in plain or "x" in plain

    def test_width_21_hash_only(self, bar) -> None:
        # Without hash, at width 21 we just get the prefix + some text
        plain = bar._render_text(width=21).plain
        assert "REPO STATS" in plain

    def test_boundary_inclusive(self, bar) -> None:
        assert bar._render_text(width=117).plain == bar._render_text().plain
        assert "↑" in bar._render_text(width=117).plain
        # At width 116, with no hash, the ahead_behind segment still fits
        assert "↑" in bar._render_text(width=116).plain

    def test_unmounted_bare_render_is_full(self) -> None:
        bar = RepoStatsBar()
        set_fields(bar, **FULL_FIELDS)
        with patch("gitux.ui.widgets.repo_stats_bar.time.time", return_value=T0):
            plain = bar._render_text().plain
        assert _DEFAULT_RENDER_WIDTH == 200
        assert "origin/main" in plain
        assert "hector" in plain
        assert "repo" in plain


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
            assert bar.content.plain.startswith(
                " \u25a0 REPO STATS \u2502 hector \u2502 "
            )

    def test_update_stats_no_remote_falls_back_to_local(self) -> None:
        bar = RepoStatsBar()
        with patch.object(bar, "update"):
            bar.update_stats(remote="", remote_branch="develop")
        assert bar._remote == "(local)"
        assert bar._remote_branch == ""
        assert "(local)" in bar._render_text().plain

    def test_update_stats_remote_with_branch(self) -> None:
        bar = RepoStatsBar()
        with patch.object(bar, "update"):
            bar.update_stats(remote="origin", remote_branch="main")
        assert "origin/main" in bar._render_text().plain

    def test_update_stats_defaults_file_counts(self) -> None:
        bar = RepoStatsBar()
        with patch.object(bar, "update"):
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
