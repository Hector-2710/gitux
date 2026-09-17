"""Tests for gitux.domain models."""

from gitux.domain import (
    CommitResult,
    FileCounts,
    FileStatus,
    OperationState,
    PushResult,
    RemoteStatus,
    RepoInfo,
    WipState,
    derive_steps,
    derive_wip_state,
)


class TestFileStatus:
    def test_staged_file(self) -> None:
        fs = FileStatus("M", " ", "file.py", None)
        assert fs.is_staged is True
        assert fs.is_unstaged is False
        assert fs.display_status == "M"

    def test_unstaged_file(self) -> None:
        fs = FileStatus(" ", "M", "file.py", None)
        assert fs.is_staged is False
        assert fs.is_unstaged is True
        assert fs.display_status == "M"

    def test_untracked_file(self) -> None:
        fs = FileStatus("?", "?", "file.py", None)
        assert fs.is_staged is False
        assert fs.is_unstaged is True

    def test_rename_display(self) -> None:
        fs = FileStatus("R", " ", "new.py", "old.py")
        assert "old.py" in fs.display_path
        assert "new.py" in fs.display_path


class TestRemoteStatus:
    def test_diverged(self) -> None:
        rs = RemoteStatus("origin", "main", ahead=2, behind=3)
        assert rs.diverged is True

    def test_not_diverged_ahead_only(self) -> None:
        rs = RemoteStatus("origin", "main", ahead=5, behind=0)
        assert rs.diverged is False

    def test_not_diverged_behind_only(self) -> None:
        rs = RemoteStatus("origin", "main", ahead=0, behind=3)
        assert rs.diverged is False


class TestCommitResult:
    def test_success(self) -> None:
        cr = CommitResult(success=True, commit_hash="abc1234")
        assert cr.success is True
        assert cr.commit_hash == "abc1234"

    def test_failure(self) -> None:
        cr = CommitResult(success=False, error="nothing staged")
        assert cr.success is False
        assert cr.error == "nothing staged"


class TestPushResult:
    def test_success(self) -> None:
        pr = PushResult(success=True, pushed_refs=["refs/heads/main"])
        assert pr.success is True
        assert len(pr.pushed_refs) == 1

    def test_failure(self) -> None:
        pr = PushResult(success=False, failed_refs=[("ref", "reason")])
        assert pr.success is False
        assert len(pr.failed_refs) == 1


class TestRepoInfo:
    def test_display_name(self) -> None:
        ri = RepoInfo(name="gitux", path="/home/user/gitux")
        assert ri.display_name == "gitux"

    def test_display_name_empty(self) -> None:
        ri = RepoInfo(name="", path="/home/user/gitux")
        assert ri.display_name == "(no name)"


class TestFileCounts:
    def _fs(self, index: str, worktree: str) -> FileStatus:
        return FileStatus(index, worktree, "path.py", None)

    def test_staged_only(self) -> None:
        assert FileCounts.from_status([self._fs("M", " ")]) == FileCounts(1, 0, 0, 0)

    def test_modified_only(self) -> None:
        assert FileCounts.from_status([self._fs(" ", "M")]) == FileCounts(0, 1, 0, 0)

    def test_am_counts_staged_only(self) -> None:
        assert FileCounts.from_status([self._fs("A", "M")]) == FileCounts(1, 0, 0, 0)

    def test_untracked_only(self) -> None:
        assert FileCounts.from_status([self._fs("?", "?")]) == FileCounts(0, 0, 1, 0)

    def test_conflict_codes(self) -> None:
        for index, worktree in ("UU", "UD", "DU", "UA", "AU", "DD", "AA"):
            assert FileCounts.from_status([self._fs(index, worktree)]) == FileCounts(
                0, 0, 0, 1
            )

    def test_mixed_partition_sums_to_len(self) -> None:
        files = [
            self._fs("M", " "),   # staged
            self._fs(" ", "M"),   # modified
            self._fs("?", "?"),   # untracked
            self._fs("U", "U"),   # conflict
            self._fs("A", "M"),   # staged (AM -> staged only)
        ]
        counts = FileCounts.from_status(files)
        assert counts == FileCounts(2, 1, 1, 1)
        assert counts.staged + counts.modified + counts.untracked + counts.conflicts == len(
            files
        )

    def test_real_19_file_sample(self) -> None:
        files = (
            [self._fs("M", " ")]                       # 1 staged
            + [self._fs(" ", "M")] * 3                 # 3 modified
            + [self._fs("?", "?")] * 15                # 15 untracked
        )
        assert len(files) == 19
        assert FileCounts.from_status(files) == FileCounts(1, 3, 15, 0)


class TestOperationState:
    def test_merge_only(self) -> None:
        assert OperationState(merge=True, rebase=False).in_progress is True

    def test_rebase_only(self) -> None:
        assert OperationState(merge=False, rebase=True).in_progress is True

    def test_neither(self) -> None:
        assert OperationState(merge=False, rebase=False).in_progress is False


class TestDeriveWipState:
    def test_operation_none_returns_unknown(self) -> None:
        counts = FileCounts(1, 1, 1, 0)
        assert derive_wip_state(counts, None, True) == WipState.UNKNOWN

    def test_merge_in_progress_zero_changes_conflict(self) -> None:
        assert (
            derive_wip_state(
                FileCounts(0, 0, 0, 0), OperationState(True, False), True
            )
            == WipState.CONFLICT
        )

    def test_conflict_count_wins_regardless_of_commits(self) -> None:
        for has_commits in (True, False):
            assert (
                derive_wip_state(
                    FileCounts(0, 0, 0, 1),
                    OperationState(False, False),
                    has_commits,
                )
                == WipState.CONFLICT
            )

    def test_no_commits_returns_unknown(self) -> None:
        assert (
            derive_wip_state(
                FileCounts(0, 0, 0, 0), OperationState(False, False), False
            )
            == WipState.UNKNOWN
        )

    def test_dirty(self) -> None:
        assert (
            derive_wip_state(
                FileCounts(1, 0, 0, 0), OperationState(False, False), True
            )
            == WipState.DIRTY
        )

    def test_clean(self) -> None:
        assert (
            derive_wip_state(
                FileCounts(0, 0, 0, 0), OperationState(False, False), True
            )
            == WipState.CLEAN
        )


class TestRepoInfoOwner:
    def test_default_owner(self) -> None:
        ri = RepoInfo(name="gitux", path="/home/u/gitux")
        assert ri.owner == ""

    def test_positional_owner_still_works(self) -> None:
        ri = RepoInfo("gitux", "/p", "owner")
        assert ri.owner == "owner"

    def test_owner_keyword(self) -> None:
        ri = RepoInfo(name="gitux", path="/p", owner="Hector-2710")
        assert ri.owner == "Hector-2710"


class TestDeriveSteps:
    def _counts(self, staged: int = 0) -> FileCounts:
        return FileCounts(staged, 0, 0, 0)

    def test_operation_in_progress_short_circuits(self) -> None:
        assert (
            derive_steps(
                self._counts(staged=1),
                RemoteStatus("origin", "main", 0, 0),
                True,
                OperationState(True, False),
            )
            == 0
        )

    def test_staged_files_step_1(self) -> None:
        assert (
            derive_steps(
                self._counts(staged=1),
                None,
                True,
                OperationState(False, False),
            )
            == 1
        )

    def test_staged_files_win_over_remote_state(self) -> None:
        # Staged files mean you're at the add step, even if remote is synced.
        assert (
            derive_steps(
                self._counts(staged=1),
                RemoteStatus("origin", "main", 0, 0),
                True,
                OperationState(False, False),
            )
            == 1
        )

    def test_no_commits_no_staged_returns_0(self) -> None:
        assert (
            derive_steps(
                self._counts(),
                None,
                False,
                OperationState(False, False),
            )
            == 0
        )

    def test_committed_step_2(self) -> None:
        assert (
            derive_steps(
                self._counts(),
                None,
                True,
                OperationState(False, False),
            )
            == 2
        )

    def test_no_upstream_stays_step_2(self) -> None:
        # remote="" means no upstream configured; ahead/behind are meaningless.
        assert (
            derive_steps(
                self._counts(),
                RemoteStatus("", "main", 0, 0),
                True,
                OperationState(False, False),
            )
            == 2
        )

    def test_ahead_of_remote_stays_step_2(self) -> None:
        assert (
            derive_steps(
                self._counts(),
                RemoteStatus("origin", "main", 2, 0),
                True,
                OperationState(False, False),
            )
            == 2
        )

    def test_fully_synced_resets_to_0(self) -> None:
        # Clean tree + synced remote → nothing pending, indicator resets.
        assert (
            derive_steps(
                self._counts(),
                RemoteStatus("origin", "main", 0, 0),
                True,
                OperationState(False, False),
            )
            == 0
        )

    def test_behind_remote_stays_step_3(self) -> None:
        # Pushed but behind → needs pull, indicator shows step 3.
        assert (
            derive_steps(
                self._counts(),
                RemoteStatus("origin", "main", 0, 3),
                True,
                OperationState(False, False),
            )
            == 3
        )

    def test_diverged_stays_step_2(self) -> None:
        assert (
            derive_steps(
                self._counts(),
                RemoteStatus("origin", "main", 2, 3),
                True,
                OperationState(False, False),
            )
            == 2
        )
