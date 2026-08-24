"""Tests for gitux.presenter.commit_presenter."""

from unittest.mock import patch

from gitux.domain import CommitResult, FileStatus, OperationState
from gitux.presenter.commit_presenter import CommitPresenter


class TestCleanMessage:
    """Tests for commit message cleaning."""

    def test_strip_whitespace(self) -> None:
        assert CommitPresenter._clean_message("  hello  ") == "hello"

    def test_strip_comment_lines(self) -> None:
        msg = "# This is a comment\nfeat: real message\n# another comment"
        result = CommitPresenter._clean_message(msg)
        assert result == "feat: real message"

    def test_empty_after_cleaning(self) -> None:
        assert CommitPresenter._clean_message("# only comments") == ""

    def test_only_whitespace(self) -> None:
        assert CommitPresenter._clean_message("   \n  \n  ") == ""

    def test_multiline_preserved(self) -> None:
        msg = "feat: add feature\n\nThis is the body\nwith details"
        result = CommitPresenter._clean_message(msg)
        assert "feat: add feature" in result
        assert "This is the body" in result


class TestCommitValidation:
    """Tests for commit validation logic."""

    @patch("gitux.presenter.commit_presenter.get_status", return_value=[])
    @patch("gitux.presenter.commit_presenter.is_detached_head", return_value=False)
    @patch(
        "gitux.presenter.commit_presenter.get_operation_state",
        return_value=OperationState(merge=False, rebase=False),
    )
    def test_commit_empty_message(self, mock_state, mock_detached, mock_status) -> None:
        presenter = CommitPresenter()
        presenter.load_status()
        result = presenter.commit("")
        assert result.success is False
        assert "empty" in result.error.lower()

    @patch("gitux.presenter.commit_presenter.get_status", return_value=[])
    @patch("gitux.presenter.commit_presenter.is_detached_head", return_value=False)
    @patch(
        "gitux.presenter.commit_presenter.get_operation_state",
        return_value=OperationState(merge=False, rebase=False),
    )
    def test_commit_no_staged(self, mock_state, mock_detached, mock_status) -> None:
        presenter = CommitPresenter()
        presenter.load_status()
        result = presenter.commit("feat: something")
        assert result.success is False
        assert "no staged" in result.error.lower()

    @patch("gitux.presenter.commit_presenter.get_status", return_value=[])
    @patch("gitux.presenter.commit_presenter.is_detached_head", return_value=True)
    @patch(
        "gitux.presenter.commit_presenter.get_operation_state",
        return_value=OperationState(merge=False, rebase=False),
    )
    def test_can_commit_detached(self, mock_state, mock_detached, mock_status) -> None:
        presenter = CommitPresenter()
        presenter.load_status()
        assert presenter.can_commit() is False


class TestGetDiff:
    @patch(
        "gitux.presenter.commit_presenter.get_untracked_file_diff",
        return_value="untracked diff",
    )
    def test_untracked_routes_to_no_index_diff(self, mock_untracked) -> None:
        presenter = CommitPresenter()
        result = presenter.get_diff(FileStatus("?", "?", "a.txt", None))
        assert result == "untracked diff"
        mock_untracked.assert_called_once_with("a.txt")

    @patch(
        "gitux.presenter.commit_presenter.get_staged_file_diff",
        return_value="staged diff",
    )
    def test_staged_routes_to_staged_diff(self, mock_staged) -> None:
        presenter = CommitPresenter()
        assert presenter.get_diff(FileStatus("M", " ", "f.py", None)) == "staged diff"
        mock_staged.assert_called_once_with("f.py")

    @patch(
        "gitux.presenter.commit_presenter.get_file_diff",
        return_value="unstaged diff",
    )
    def test_unstaged_routes_to_file_diff(self, mock_file) -> None:
        presenter = CommitPresenter()
        assert presenter.get_diff(FileStatus(" ", "M", "f.py", None)) == "unstaged diff"
        mock_file.assert_called_once_with("f.py")


class TestStageUnstage:
    """Tests for file staging/unstaging."""

    @patch("gitux.presenter.commit_presenter.git_stage")
    @patch("gitux.presenter.commit_presenter.get_status", return_value=[])
    def test_stage_calls_git(self, mock_status, mock_stage) -> None:
        presenter = CommitPresenter()
        presenter.load_status()
        presenter.stage_files(["file.py"])
        mock_stage.assert_called_once_with(["file.py"])

    @patch("gitux.presenter.commit_presenter.git_unstage")
    @patch("gitux.presenter.commit_presenter.get_status", return_value=[])
    def test_unstage_calls_git(self, mock_status, mock_unstage) -> None:
        presenter = CommitPresenter()
        presenter.load_status()
        presenter.unstage_files(["file.py"])
        mock_unstage.assert_called_once_with(["file.py"])


class TestCanCommit:
    @patch(
        "gitux.presenter.commit_presenter.get_status",
        return_value=[FileStatus("M", " ", "file.py", None)],
    )
    @patch("gitux.presenter.commit_presenter.is_detached_head", return_value=False)
    @patch(
        "gitux.presenter.commit_presenter.get_operation_state",
        return_value=OperationState(merge=True, rebase=False),
    )
    def test_false_during_merge_with_staged(self, mock_state, mock_detached, mock_status) -> None:
        presenter = CommitPresenter()
        presenter.load_status()
        assert presenter.can_commit() is False

    @patch(
        "gitux.presenter.commit_presenter.get_status",
        return_value=[FileStatus("M", " ", "file.py", None)],
    )
    @patch("gitux.presenter.commit_presenter.is_detached_head", return_value=False)
    @patch(
        "gitux.presenter.commit_presenter.get_operation_state",
        return_value=OperationState(merge=False, rebase=False),
    )
    def test_true_with_staged_no_operation(self, mock_state, mock_detached, mock_status) -> None:
        presenter = CommitPresenter()
        presenter.load_status()
        assert presenter.can_commit() is True

    @patch("gitux.presenter.commit_presenter.get_status", return_value=[])
    @patch("gitux.presenter.commit_presenter.is_detached_head", return_value=False)
    @patch(
        "gitux.presenter.commit_presenter.get_operation_state",
        return_value=OperationState(merge=False, rebase=False),
    )
    def test_false_without_staged(self, mock_state, mock_detached, mock_status) -> None:
        presenter = CommitPresenter()
        presenter.load_status()
        assert presenter.can_commit() is False
