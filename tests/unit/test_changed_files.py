"""Tests for gitux.ui.widgets.changed_files.ChangedFilesPanel."""

from unittest.mock import patch

from gitux.domain import FileStatus
from gitux.ui.widgets.changed_files import _MAX_PATH_CHARS, ChangedFilesPanel


def _staged(path: str) -> FileStatus:
    return FileStatus("M", " ", path, None)


def _unstaged(path: str) -> FileStatus:
    return FileStatus(" ", "M", path, None)


class TestTruncatePath:
    def test_short_path_unchanged(self) -> None:
        panel = ChangedFilesPanel()
        assert panel._truncate_path("src/main.py") == "src/main.py"

    def test_len_40_unchanged(self) -> None:
        panel = ChangedFilesPanel()
        path = "a" * 40
        assert len(path) == 40
        assert panel._truncate_path(path) == path

    def test_len_41_truncates_to_exactly_40(self) -> None:
        panel = ChangedFilesPanel()
        path = "b" * 41
        result = panel._truncate_path(path)
        assert result == path[:_MAX_PATH_CHARS - 2] + ".."
        assert len(result) == 40

    def test_long_path_truncated(self) -> None:
        panel = ChangedFilesPanel()
        path = "c" * 100
        result = panel._truncate_path(path)
        assert result == path[:38] + ".."
        assert len(result) == 40

    def test_rename_path_truncated_as_one_string(self) -> None:
        panel = ChangedFilesPanel()
        path = "src/very/long/old_directory/old_file_name.py -> src/very/long/new_directory/new_file_name.py"
        assert len(path) > _MAX_PATH_CHARS
        result = panel._truncate_path(path)
        assert len(result) <= _MAX_PATH_CHARS
        assert result == path[:38] + ".."


class TestRowForIndex:
    def test_staged_only(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [_staged("s0.py"), _staged("s1.py"), _staged("s2.py")]
        assert panel._row_for_index(0) == 1
        assert panel._row_for_index(2) == 3

    def test_unstaged_only(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [_unstaged("u0.py"), _unstaged("u1.py")]
        assert panel._row_for_index(0) == 3
        assert panel._row_for_index(1) == 4

    def test_mixed_boundary(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [_staged("s0.py"), _staged("s1.py"), _unstaged("u0.py"), _unstaged("u1.py")]
        assert panel._row_for_index(1) == 2
        assert panel._row_for_index(2) == 4

    def test_empty_list_returns_zero(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = []
        assert panel._row_for_index(0) == 0


class TestScrollToCursor:
    def test_scrolls_to_cursor_row(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [_staged("s0.py"), _staged("s1.py"), _unstaged("u0.py")]
        panel._cursor_index = 1
        with patch.object(panel, "scroll_to") as mock_scroll_to:
            panel._scroll_to_cursor()
            mock_scroll_to.assert_called_once_with(y=2, animate=False)

    def test_scrolls_to_first_unstaged_row(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [_staged("s0.py"), _staged("s1.py"), _unstaged("u0.py"), _unstaged("u1.py")]
        panel._cursor_index = 2
        with patch.object(panel, "scroll_to") as mock_scroll_to:
            panel._scroll_to_cursor()
            mock_scroll_to.assert_called_once_with(y=4, animate=False)

    def test_empty_list_noop(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = []
        panel._cursor_index = 0
        with patch.object(panel, "scroll_to") as mock_scroll_to:
            panel._scroll_to_cursor()
            mock_scroll_to.assert_not_called()

    def test_cursor_zero_mixed_scrolls_to_top(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [
            _staged("s0.py"),
            _staged("s1.py"),
            _unstaged("u0.py"),
            _unstaged("u1.py"),
        ]
        panel._cursor_index = 0
        with patch.object(panel, "scroll_to") as mock_scroll_to:
            panel._scroll_to_cursor()
            mock_scroll_to.assert_called_once_with(y=0, animate=False)

    def test_cursor_zero_unstaged_only_scrolls_to_top(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [_unstaged("u0.py"), _unstaged("u1.py")]
        panel._cursor_index = 0
        with patch.object(panel, "scroll_to") as mock_scroll_to:
            panel._scroll_to_cursor()
            mock_scroll_to.assert_called_once_with(y=0, animate=False)

    def test_cursor_zero_staged_only_scrolls_to_top(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [_staged("s0.py"), _staged("s1.py")]
        panel._cursor_index = 0
        with patch.object(panel, "scroll_to") as mock_scroll_to:
            panel._scroll_to_cursor()
            mock_scroll_to.assert_called_once_with(y=0, animate=False)

    def test_set_files_at_cursor_zero_scrolls_to_top(self) -> None:
        panel = ChangedFilesPanel()
        panel._cursor_index = 0
        with patch.object(panel, "scroll_to") as mock_scroll_to:
            panel.set_files([_staged(f"f{i:03d}.py") for i in range(60)])
            mock_scroll_to.assert_called_once_with(y=0, animate=False)


class TestRenderFiles:
    def test_root_text_no_wrap(self) -> None:
        panel = ChangedFilesPanel()
        panel._files = [_staged("src/main.py"), _unstaged("src/other.py")]
        text = panel._render_files()
        assert text.no_wrap is True
