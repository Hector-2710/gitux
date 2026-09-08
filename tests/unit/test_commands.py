"""Tests for gitux.git.commands with mocked subprocess."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from gitux.domain import HeadSummary, OperationState
from gitux.git import GitError
from gitux.git.commands import (
    _COMMIT_DETAILS_FORMAT,
    _extract_owner,
    _extract_repo_name,
    _run_tolerant,
    _try_config,
    commit,
    get_branches,
    get_commit_details,
    get_current_branch,
    get_default_branch,
    get_git_dir,
    get_head_summary,
    get_operation_state,
    get_repo_info,
    get_status,
    get_untracked_file_diff,
    get_user,
    is_merge_in_progress,
    is_rebase_in_progress,
    push,
    stage,
    switch_branch,
    unstage,
)


class TestGetStatus:
    @patch("gitux.git.runner.subprocess.run")
    def test_parses_output(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="M  src/main.py\0A  new.py\0",
            stderr="",
        )
        result = get_status()
        assert len(result) == 2
        assert result[0].path == "src/main.py"

    @patch("gitux.git.runner.subprocess.run")
    def test_expands_untracked_directories(self, mock_run) -> None:
        """Status must use -uall so untracked dirs list every file individually."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        get_status()
        args = mock_run.call_args[0][0]
        assert "-uall" in args


class TestStage:
    @patch("gitux.git.runner.subprocess.run")
    def test_calls_git_add(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        stage(["file.py"])
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "add" in args
        assert "file.py" in args

    @patch("gitux.git.runner.subprocess.run")
    def test_empty_paths_noop(self, mock_run) -> None:
        stage([])
        mock_run.assert_not_called()


class TestUnstage:
    @patch("gitux.git.runner.subprocess.run")
    def test_calls_git_reset(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        unstage(["file.py"])
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "reset" in args


class TestCommit:
    @patch("gitux.git.runner.subprocess.run")
    def test_returns_hash(self, mock_run) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="abc1234\n", stderr=""),  # rev-parse
        ]
        result = commit("feat: test")
        assert result == "abc1234"


class TestExtractRepoName:
    def test_https_with_git_suffix(self) -> None:
        assert _extract_repo_name("https://github.com/user/gitux.git") == "gitux"

    def test_https_without_git_suffix(self) -> None:
        assert _extract_repo_name("https://github.com/user/gitux") == "gitux"

    def test_ssh_style(self) -> None:
        assert _extract_repo_name("git@github.com:user/gitux.git") == "gitux"

    def test_ssh_without_git_suffix(self) -> None:
        assert _extract_repo_name("git@github.com:user/gitux") == "gitux"

    def test_nested_path(self) -> None:
        url = "https://gitlab.com/group/subgroup/my-repo.git"
        assert _extract_repo_name(url) == "my-repo"


class TestGetRepoInfo:
    @patch("gitux.git.runner.subprocess.run")
    def test_with_origin(self, mock_run) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/home/user/gitux\n", stderr=""),  # rev-parse
            MagicMock(returncode=0, stdout="https://github.com/user/gitux.git\n", stderr=""),  # remote get-url
        ]
        info = get_repo_info()
        assert info.name == "gitux"
        assert info.path == "/home/user/gitux"
        assert info.owner == "user"
        assert info.display_name == "gitux"

    @patch("gitux.git.runner.subprocess.run")
    def test_no_remote_falls_back_to_toplevel_basename(self, mock_run) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/home/user/gitux\n", stderr=""),  # rev-parse
            MagicMock(returncode=128, stdout="", stderr="error"),  # remote get-url origin fails
            MagicMock(returncode=128, stdout="", stderr="error"),  # git remote fails too
        ]
        info = get_repo_info()
        assert info.name == "gitux"
        assert info.path == "/home/user/gitux"
        assert info.owner == ""
        assert info.display_name == "gitux"

    @patch("gitux.git.runner.subprocess.run")
    def test_no_remote_uses_toplevel_basename(self, mock_run) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/tmp/x/mi-proyecto\n", stderr=""),  # rev-parse
            MagicMock(returncode=128, stdout="", stderr="error"),  # remote get-url origin fails
            MagicMock(returncode=128, stdout="", stderr="error"),  # git remote fails too
        ]
        info = get_repo_info()
        assert info.name == "mi-proyecto"
        assert info.path == "/tmp/x/mi-proyecto"
        assert info.owner == ""
        assert info.display_name == "mi-proyecto"

    @patch("gitux.git.runner.subprocess.run")
    def test_remote_name_takes_priority(self, mock_run) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/tmp/x/mi-proyecto\n", stderr=""),  # rev-parse
            MagicMock(returncode=0, stdout="https://github.com/user/remote-repo.git\n", stderr=""),  # remote get-url
        ]
        info = get_repo_info()
        assert info.name == "remote-repo"
        assert info.path == "/tmp/x/mi-proyecto"
        assert info.owner == "user"


class TestSwitchBranch:
    @patch("gitux.git.runner.subprocess.run")
    def test_switches_branch(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        switch_branch("feature/x")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "switch" in args
        assert "feature/x" in args

    @patch("gitux.git.runner.subprocess.run")
    def test_raises_git_error_on_failure(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="error")
        with pytest.raises(GitError):
            switch_branch("feature/x")


class TestGetBranches:
    @patch("gitux.git.runner.subprocess.run")
    def test_skips_detached_head_marker(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="* main\n  feature/x\n* (HEAD detached at abc1234)\n",
            stderr="",
        )
        assert get_branches() == ["main", "feature/x"]

    @patch("gitux.git.runner.subprocess.run")
    def test_parses_plain_branch_list(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  main\n  feature/x\n",
            stderr="",
        )
        assert get_branches() == ["main", "feature/x"]


class TestGetCurrentBranch:
    @patch("gitux.git.runner.subprocess.run")
    def test_uses_show_current(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n", stderr="")
        assert get_current_branch() == "main"
        args = mock_run.call_args[0][0]
        assert "branch" in args
        assert "--show-current" in args

    @patch("gitux.git.runner.subprocess.run")
    def test_detached_returns_empty(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        assert get_current_branch() == ""


class TestTryConfig:
    @patch("gitux.git.runner.subprocess.run")
    def test_config_miss_swallowed(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        assert _try_config("user.name") == ""


class TestGetUser:
    @patch("gitux.git.config._try_config", return_value="hector")
    def test_name_set_returns_name(self, mock_config) -> None:
        assert get_user() == "hector"
        mock_config.assert_called_once_with("user.name")

    @patch("gitux.git.config._try_config", side_effect=["", "hector@example.com"])
    @patch("gitux.git.config._os_login", return_value="fallback")
    def test_empty_name_falls_to_email(self, mock_login, mock_config) -> None:
        assert get_user() == "hector@example.com"
        mock_login.assert_not_called()

    @patch("gitux.git.config._try_config", return_value="")
    @patch("gitux.git.config._os_login", return_value="hector")
    def test_both_empty_falls_to_os_login(self, mock_login, mock_config) -> None:
        assert get_user() == "hector"

    @patch("gitux.git.config._try_config", return_value="")
    def test_oserror_falls_back_to_env(self, mock_config) -> None:
        fake_os = MagicMock()
        fake_os.getlogin.side_effect = OSError("no tty")
        fake_os.environ = {"USER": "envuser"}
        with patch("gitux.git.config.os", fake_os):
            assert get_user() == "envuser"

    @patch("gitux.git.config._try_config", return_value="")
    def test_all_empty_returns_empty(self, mock_config) -> None:
        fake_os = MagicMock()
        fake_os.getlogin.side_effect = OSError("no tty")
        fake_os.environ = {}
        with patch("gitux.git.config.os", fake_os):
            assert get_user() == ""

    @patch("gitux.git.config._try_config", return_value="")
    @patch("gitux.git.config._os_login", return_value="hector")
    def test_config_miss_never_raises(self, mock_login, mock_config) -> None:
        assert get_user() == "hector"


class TestGetHeadSummary:
    @patch("gitux.git.runner.subprocess.run")
    def test_returns_summary(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="66f7291\tfeat: x\t1785784746\n", stderr=""
        )
        assert get_head_summary() == HeadSummary("66f7291", "feat: x", 1785784746)

    @patch("gitux.git.runner.subprocess.run")
    def test_too_few_fields_returns_none(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="66f7291\tfeat: x\n", stderr="")
        assert get_head_summary() is None

    @patch("gitux.git.runner.subprocess.run")
    def test_non_integer_epoch_returns_none(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="66f7291\tfeat: x\tnotanint\n", stderr=""
        )
        assert get_head_summary() is None

    @patch("gitux.git.runner.subprocess.run")
    def test_empty_repo_propagates_git_error(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="error")
        with pytest.raises(GitError):
            get_head_summary()


class TestGetDefaultBranch:
    @patch("gitux.git.runner.subprocess.run")
    def test_head_line_authoritative(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  origin/HEAD -> origin/main\n  origin/develop\n",
            stderr="",
        )
        assert get_default_branch() == "main"

    @patch("gitux.git.runner.subprocess.run")
    def test_origin_main_convention(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="  origin/main\n", stderr=""
        )
        assert get_default_branch() == "main"

    @patch("gitux.git.runner.subprocess.run")
    def test_origin_master_convention(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="  origin/master\n", stderr=""
        )
        assert get_default_branch() == "master"

    @patch("gitux.git.runner.subprocess.run")
    def test_neither_returns_empty(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="  origin/develop\n", stderr=""
        )
        assert get_default_branch() == ""


class TestGetGitDir:
    @patch("gitux.git.runner.subprocess.run")
    def test_returns_git_dir(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout=".git\n", stderr="")
        assert get_git_dir() == ".git"


class TestGetOperationState:
    def test_merge_in_progress(self, tmp_path) -> None:
        (tmp_path / "MERGE_HEAD").touch()
        with patch("gitux.git.repo.get_git_dir", return_value=str(tmp_path)):
            state = get_operation_state()
        assert state == OperationState(merge=True, rebase=False)
        assert state.in_progress is True

    def test_rebase_merge_in_progress(self, tmp_path) -> None:
        (tmp_path / "rebase-merge").mkdir()
        with patch("gitux.git.repo.get_git_dir", return_value=str(tmp_path)):
            state = get_operation_state()
        assert state == OperationState(merge=False, rebase=True)

    def test_rebase_apply_in_progress(self, tmp_path) -> None:
        (tmp_path / "rebase-apply").mkdir()
        with patch("gitux.git.repo.get_git_dir", return_value=str(tmp_path)):
            state = get_operation_state()
        assert state == OperationState(merge=False, rebase=True)

    def test_none_in_progress(self, tmp_path) -> None:
        with patch("gitux.git.repo.get_git_dir", return_value=str(tmp_path)):
            state = get_operation_state()
        assert state == OperationState(merge=False, rebase=False)
        assert state.in_progress is False


class TestMergeRebaseWrappers:
    def test_merge_wrapper_true(self, tmp_path) -> None:
        (tmp_path / "MERGE_HEAD").touch()
        with patch("gitux.git.repo.get_git_dir", return_value=str(tmp_path)):
            assert is_merge_in_progress() is True

    def test_merge_wrapper_false(self, tmp_path) -> None:
        with patch("gitux.git.repo.get_git_dir", return_value=str(tmp_path)):
            assert is_merge_in_progress() is False

    def test_rebase_wrapper_true(self, tmp_path) -> None:
        (tmp_path / "rebase-merge").mkdir()
        with patch("gitux.git.repo.get_git_dir", return_value=str(tmp_path)):
            assert is_rebase_in_progress() is True

    def test_rebase_wrapper_false(self, tmp_path) -> None:
        with patch("gitux.git.repo.get_git_dir", return_value=str(tmp_path)):
            assert is_rebase_in_progress() is False


class TestExtractOwner:
    def test_https(self) -> None:
        assert _extract_owner("https://github.com/Hector-2710/gitux.git") == "Hector-2710"

    def test_ssh(self) -> None:
        assert _extract_owner("git@github.com:user/repo.git") == "user"

    def test_nested_path(self) -> None:
        assert _extract_owner("https://gitlab.com/group/subgroup/my-repo.git") == "subgroup"

    def test_no_owner(self) -> None:
        assert _extract_owner("https://github.com/gitux.git") == ""


class TestRunTolerant:
    @patch("gitux.git.runner.subprocess.run")
    def test_allowed_return_code_returns_result(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="diff", stderr="")
        result = _run_tolerant(
            ["diff", "--no-index", "/dev/null", "a.txt"],
            allowed_return_codes={0, 1},
        )
        assert result.stdout == "diff"

    @patch("gitux.git.runner.subprocess.run")
    def test_unexpected_return_code_raises(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="boom")
        with pytest.raises(GitError):
            _run_tolerant(
                ["diff", "--no-index", "/dev/null", "a.txt"],
                allowed_return_codes={0, 1},
            )

    @patch("gitux.git.runner.subprocess.run")
    def test_timeout_raises(self, mock_run) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)
        with pytest.raises(GitError):
            _run_tolerant(["diff"], allowed_return_codes={0, 1})

    @patch("gitux.git.runner.subprocess.run")
    def test_file_not_found_raises(self, mock_run) -> None:
        mock_run.side_effect = FileNotFoundError("git")
        with pytest.raises(GitError):
            _run_tolerant(["diff"], allowed_return_codes={0, 1})


class TestGetUntrackedFileDiff:
    DIFF = (
        "diff --git a/src/hello.txt b/src/hello.txt\n"
        "new file mode 100644\n"
        "index 0000000..8792505\n"
        "--- /dev/null\n"
        "+++ b/src/hello.txt\n"
        "@@ -0,0 +1,3 @@\n"
        "+line1\n"
        "+line2 changed\n"
        "+line3\n"
    )

    @patch("gitux.git.runner.subprocess.run")
    def test_rc1_text_diff_returns_stdout(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout=self.DIFF, stderr="")
        result = get_untracked_file_diff("src/hello.txt")
        assert result == self.DIFF
        assert mock_run.call_args[0][0] == [
            "git", "diff", "--no-index", "/dev/null", "src/hello.txt",
        ]

    @patch("gitux.git.runner.subprocess.run")
    def test_binary_returns_empty(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="Binary files /dev/null and b/x differ\n",
            stderr="",
        )
        assert get_untracked_file_diff("x") == ""

    @patch("gitux.git.runner.subprocess.run")
    def test_empty_file_metadata_only_returns_empty(self, mock_run) -> None:
        metadata = (
            "diff --git a/empty.txt b/empty.txt\n"
            "new file mode 100644\n"
            "index 0000000..e69de29\n"
            "--- /dev/null\n"
            "+++ b/empty.txt\n"
        )
        mock_run.return_value = MagicMock(returncode=1, stdout=metadata, stderr="")
        assert get_untracked_file_diff("empty.txt") == ""

    @patch("gitux.git.runner.subprocess.run")
    def test_rc0_no_hunks_returns_empty(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="diff --git a/empty.txt b/empty.txt\n",
            stderr="",
        )
        assert get_untracked_file_diff("empty.txt") == ""

    @patch("gitux.git.runner.subprocess.run")
    def test_rc2_returns_empty(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="fatal")
        assert get_untracked_file_diff("x") == ""

    @patch("gitux.git.runner.subprocess.run")
    def test_timeout_returns_empty(self, mock_run) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)
        assert get_untracked_file_diff("x") == ""

    @patch("gitux.git.runner.subprocess.run")
    def test_path_with_spaces_single_arg(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout=self.DIFF, stderr="")
        get_untracked_file_diff("new dir/spaced file.txt")
        assert mock_run.call_args[0][0] == [
            "git", "diff", "--no-index", "/dev/null", "new dir/spaced file.txt",
        ]

    @patch("gitux.git.runner.subprocess.run")
    def test_text_diff_mentioning_binary_phrase_is_not_binary(self, mock_run) -> None:
        """A text diff whose content contains the literal 'Binary files' string
        must not be mistaken for a binary diff (regression: status.py itself
        contains that phrase in its source, which tripped the old substring check).
        """
        diff = (
            "diff --git a/src/x.py b/src/x.py\n"
            "new file mode 100644\n"
            "index 0000000..abc1234\n"
            "--- /dev/null\n"
            "+++ b/src/x.py\n"
            "@@ -0,0 +1,3 @@\n"
            '+    if "Binary files" in result.stdout:\n'
            '+        return ""\n'
        )
        mock_run.return_value = MagicMock(returncode=1, stdout=diff, stderr="")
        assert get_untracked_file_diff("src/x.py") == diff


class TestGetCommitDetails:
    @patch("gitux.git.runner.subprocess.run")
    def test_returns_show_output(self, mock_run) -> None:
        sample = (
            "c4474af Jane Doe <jane@example.com>\n"
            "2024-01-01 10:00:00 +0000\n\n"
            "feat: add details\n\n"
            "body line\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=sample, stderr="")
        assert get_commit_details("c4474af") == sample
        args = mock_run.call_args[0][0]
        assert args == [
            "git",
            "show",
            f"--format={_COMMIT_DETAILS_FORMAT}",
            "--stat",
            "--date=iso",
            "c4474af",
        ]

    @patch("gitux.git.runner.subprocess.run")
    def test_raises_on_failure(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal")
        with pytest.raises(GitError):
            get_commit_details("c4474af")
