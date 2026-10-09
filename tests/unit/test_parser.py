"""Tests for gitux.git.parser."""

from gitux.domain import FileStatus
from gitux.git.parser import parse_push_output, parse_status


class TestParseStatus:
    """Tests for porcelain v1 -z status parsing."""

    def test_empty_input(self) -> None:
        assert parse_status("") == []

    def test_single_modified_file(self) -> None:
        # XY = "M " (staged modified, no worktree change) + space + path
        raw = "M  src/main.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.index_status == "M"
        assert f.worktree_status == " "
        assert f.path == "src/main.py"
        assert f.old_path is None
        assert f.is_staged is True
        assert f.is_unstaged is False

    def test_untracked_file(self) -> None:
        raw = "?? config.json\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.index_status == "?"
        assert f.worktree_status == "?"
        assert f.is_staged is False
        assert f.display_status == "u"

    def test_renamed_file(self) -> None:
        # Real git -z format: XY + space + new path, then old path (order reversed
        # from the human "old -> new" display, and no score).
        raw = "R  new_name.py\0old_name.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.index_status == "R"
        assert f.old_path == "old_name.py"
        assert f.path == "new_name.py"
        assert "old_name.py" in f.display_path
        assert "new_name.py" in f.display_path

    def test_multiple_files(self) -> None:
        raw = "M  file1.py\0A  file2.py\0?? untracked.txt\0"
        result = parse_status(raw)
        assert len(result) == 3

    def test_deleted_file(self) -> None:
        raw = "D  deleted.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        assert result[0].index_status == "D"
        assert result[0].display_status == "D"

    def test_copied_file(self) -> None:
        raw = "C  new.py\0old.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.index_status == "C"
        assert f.old_path == "old.py"
        assert f.path == "new.py"

    def test_renamed_and_modified_file(self) -> None:
        # Rename with worktree modification: XY = "RM", worktree status preserved.
        raw = "RM new.py\0old.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.index_status == "R"
        assert f.worktree_status == "M"
        assert f.old_path == "old.py"
        assert f.path == "new.py"
        assert f.is_staged is True
        assert f.is_unstaged is True

    def test_rename_missing_old_path(self) -> None:
        # Truncated input: old_path part is absent, so it defaults to "".
        raw = "R  new.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.path == "new.py"
        assert f.old_path == ""

    def test_rename_with_spaces_in_path(self) -> None:
        # Paths with spaces are preserved as-is in the -z format.
        raw = "R  my new.py\0my old.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.path == "my new.py"
        assert f.old_path == "my old.py"

    def test_worktree_only_change(self) -> None:
        raw = " M file.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.index_status == " "
        assert f.worktree_status == "M"
        assert f.is_staged is False
        assert f.is_unstaged is True

    def test_conflict(self) -> None:
        raw = "UU file.py\0"
        result = parse_status(raw)
        assert len(result) == 1
        f = result[0]
        assert f.index_status == "U"
        assert f.worktree_status == "U"
        assert f.display_status == "U"

    def test_empty_parts_are_skipped(self) -> None:
        # Trailing NULs and empty parts in the middle must be ignored.
        raw = "M  a.py\0\0?? b.py\0"
        result = parse_status(raw)
        assert len(result) == 2
        assert result[0].path == "a.py"
        assert result[1].path == "b.py"


class TestParsePushOutput:
    """Tests for git push --porcelain output parsing."""

    def test_single_success(self) -> None:
        ok, fail = parse_push_output("ok refs/heads/main\n")
        assert ok == ["refs/heads/main"]
        assert fail == []

    def test_single_failure(self) -> None:
        ok, fail = parse_push_output("ng refs/heads/dev permission denied\n")
        assert ok == []
        assert len(fail) == 1
        assert fail[0][0] == "refs/heads/dev"
        assert "permission" in fail[0][1]

    def test_mixed(self) -> None:
        output = "ok refs/heads/main\nng refs/heads/dev auth failed\nok refs/tags/v1.0\n"
        ok, fail = parse_push_output(output)
        assert len(ok) == 2
        assert len(fail) == 1

    def test_empty(self) -> None:
        ok, fail = parse_push_output("")
        assert ok == []
        assert fail == []
