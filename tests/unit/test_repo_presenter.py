"""Tests for gitux.presenter.repo_presenter.RepoPresenter."""

from unittest.mock import patch

import pytest

from gitux.domain import HeadSummary, OperationState, RemoteStatus, RepoInfo
from gitux.git.exceptions import GitError
from gitux.presenter.repo_presenter import RepoPresenter


class TestGetCurrentBranch:
    """Tests for RepoPresenter.get_current_branch."""

    @patch("gitux.presenter.repo_presenter.get_current_branch", return_value="main")
    def test_returns_branch_name(self, mock_branch) -> None:
        presenter = RepoPresenter()
        assert presenter.get_current_branch() == "main"

    @patch(
        "gitux.presenter.repo_presenter.get_current_branch",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_empty_on_error(self, mock_branch) -> None:
        presenter = RepoPresenter()
        assert presenter.get_current_branch() == ""


class TestIsDetachedHead:
    """Tests for RepoPresenter.is_detached_head."""

    @patch("gitux.presenter.repo_presenter.is_detached_head", return_value=True)
    def test_detached_true(self, mock_detached) -> None:
        presenter = RepoPresenter()
        assert presenter.is_detached_head() is True

    @patch("gitux.presenter.repo_presenter.is_detached_head", return_value=False)
    def test_detached_false(self, mock_detached) -> None:
        presenter = RepoPresenter()
        assert presenter.is_detached_head() is False

    @patch(
        "gitux.presenter.repo_presenter.is_detached_head",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_false_on_error(self, mock_detached) -> None:
        presenter = RepoPresenter()
        assert presenter.is_detached_head() is False


class TestGetRemoteStatus:
    """Tests for RepoPresenter.get_remote_status."""

    @patch(
        "gitux.presenter.repo_presenter.get_remote_status",
        return_value=RemoteStatus(remote="origin", branch="main", ahead=3, behind=0),
    )
    def test_returns_remote_status(self, mock_status) -> None:
        presenter = RepoPresenter()
        status = presenter.get_remote_status()
        assert status is not None
        assert status.remote == "origin"
        assert status.ahead == 3
        assert status.behind == 0

    @patch(
        "gitux.presenter.repo_presenter.get_remote_status",
        side_effect=GitError("no remote"),
    )
    def test_returns_none_on_error(self, mock_status) -> None:
        presenter = RepoPresenter()
        assert presenter.get_remote_status() is None


class TestGetRepoInfo:
    """Tests for RepoPresenter.get_repo_info."""

    @patch(
        "gitux.presenter.repo_presenter.get_repo_info",
        return_value=RepoInfo(name="gitux", path="/home/user/gitux"),
    )
    def test_returns_repo_info(self, mock_info) -> None:
        presenter = RepoPresenter()
        info = presenter.get_repo_info()
        assert info is not None
        assert info.name == "gitux"
        assert info.path == "/home/user/gitux"

    @patch(
        "gitux.presenter.repo_presenter.get_repo_info",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_none_on_error(self, mock_info) -> None:
        presenter = RepoPresenter()
        assert presenter.get_repo_info() is None


class TestGetCommitLog:
    """Tests for RepoPresenter.get_commit_log."""

    @patch(
        "gitux.presenter.repo_presenter.git_get_commit_log",
        return_value="* abc1234 feat: add feature\n* def5678 fix: bug",
    )
    def test_returns_log_text(self, mock_log) -> None:
        presenter = RepoPresenter()
        log = presenter.get_commit_log(2)
        assert "abc1234" in log
        assert "def5678" in log
        mock_log.assert_called_once_with(2)

    @patch(
        "gitux.presenter.repo_presenter.git_get_commit_log",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_empty_on_error(self, mock_log) -> None:
        presenter = RepoPresenter()
        assert presenter.get_commit_log(30) == ""


class TestGetCommitDetails:
    """Tests for RepoPresenter.get_commit_details."""

    @patch(
        "gitux.presenter.repo_presenter.git_get_commit_details",
        return_value="c4474af Jane Doe <jane@example.com>\n2024-01-01\n",
    )
    def test_returns_detail_text(self, mock_details) -> None:
        presenter = RepoPresenter()
        text = presenter.get_commit_details("c4474af")
        assert "c4474af" in text
        assert "Jane Doe" in text
        mock_details.assert_called_once_with("c4474af")

    @patch(
        "gitux.presenter.repo_presenter.git_get_commit_details",
        side_effect=GitError("bad revision"),
    )
    def test_returns_empty_on_error(self, mock_details) -> None:
        presenter = RepoPresenter()
        assert presenter.get_commit_details("c4474af") == ""


class TestGetBranches:
    """Tests for RepoPresenter.get_branches."""

    @patch(
        "gitux.presenter.repo_presenter.git_get_branches",
        return_value=["main", "feature/x"],
    )
    def test_returns_branch_list(self, mock_branches) -> None:
        presenter = RepoPresenter()
        assert presenter.get_branches() == ["main", "feature/x"]

    @patch(
        "gitux.presenter.repo_presenter.git_get_branches",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_empty_on_error(self, mock_branches) -> None:
        presenter = RepoPresenter()
        assert presenter.get_branches() == []


class TestSwitchBranch:
    """Tests for RepoPresenter.switch_branch."""

    @patch("gitux.presenter.repo_presenter.git_switch_branch")
    def test_calls_git_switch_branch(self, mock_switch) -> None:
        presenter = RepoPresenter()
        presenter.switch_branch("feature/x")
        mock_switch.assert_called_once_with("feature/x")

    @patch(
        "gitux.presenter.repo_presenter.git_switch_branch",
        side_effect=GitError("dirty working tree"),
    )
    def test_propagates_git_error(self, mock_switch) -> None:
        presenter = RepoPresenter()
        with pytest.raises(GitError):
            presenter.switch_branch("feature/x")


class TestGetUser:
    @patch("gitux.presenter.repo_presenter.git_get_user", return_value="hector")
    def test_returns_user(self, mock_user) -> None:
        presenter = RepoPresenter()
        assert presenter.get_user() == "hector"

    @patch(
        "gitux.presenter.repo_presenter.git_get_user",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_empty_on_error(self, mock_user) -> None:
        presenter = RepoPresenter()
        assert presenter.get_user() == ""


class TestGetHeadSummary:
    @patch(
        "gitux.presenter.repo_presenter.git_get_head_summary",
        return_value=HeadSummary("66f7291", "feat: x", 1785784746),
    )
    def test_returns_summary(self, mock_summary) -> None:
        presenter = RepoPresenter()
        summary = presenter.get_head_summary()
        assert summary is not None
        assert summary.short_hash == "66f7291"
        assert summary.subject == "feat: x"

    @patch(
        "gitux.presenter.repo_presenter.git_get_head_summary",
        side_effect=GitError("empty repo"),
    )
    def test_returns_none_on_error(self, mock_summary) -> None:
        presenter = RepoPresenter()
        assert presenter.get_head_summary() is None


class TestGetDefaultBranch:
    @patch("gitux.presenter.repo_presenter.git_get_default_branch", return_value="main")
    def test_returns_default_branch(self, mock_branch) -> None:
        presenter = RepoPresenter()
        assert presenter.get_default_branch() == "main"

    @patch(
        "gitux.presenter.repo_presenter.git_get_default_branch",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_empty_on_error(self, mock_branch) -> None:
        presenter = RepoPresenter()
        assert presenter.get_default_branch() == ""


class TestGetOperationState:
    @patch(
        "gitux.presenter.repo_presenter.git_get_operation_state",
        return_value=OperationState(merge=True, rebase=False),
    )
    def test_returns_state(self, mock_state) -> None:
        presenter = RepoPresenter()
        state = presenter.get_operation_state()
        assert state is not None
        assert state.in_progress is True

    @patch(
        "gitux.presenter.repo_presenter.git_get_operation_state",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_none_on_error(self, mock_state) -> None:
        presenter = RepoPresenter()
        assert presenter.get_operation_state() is None


class TestIsMergeInProgress:
    @patch(
        "gitux.presenter.repo_presenter.git_is_merge_in_progress", return_value=True
    )
    def test_merge_true(self, mock_merge) -> None:
        presenter = RepoPresenter()
        assert presenter.is_merge_in_progress() is True

    @patch(
        "gitux.presenter.repo_presenter.git_is_merge_in_progress",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_false_on_error(self, mock_merge) -> None:
        presenter = RepoPresenter()
        assert presenter.is_merge_in_progress() is False


class TestIsRebaseInProgress:
    @patch(
        "gitux.presenter.repo_presenter.git_is_rebase_in_progress", return_value=True
    )
    def test_rebase_true(self, mock_rebase) -> None:
        presenter = RepoPresenter()
        assert presenter.is_rebase_in_progress() is True

    @patch(
        "gitux.presenter.repo_presenter.git_is_rebase_in_progress",
        side_effect=GitError("not a git repo"),
    )
    def test_returns_false_on_error(self, mock_rebase) -> None:
        presenter = RepoPresenter()
        assert presenter.is_rebase_in_progress() is False
