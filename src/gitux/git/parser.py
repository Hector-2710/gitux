"""Utilities for parsing git porcelain output."""

from gitux.domain import FileStatus


def parse_status(raw: str) -> list[FileStatus]:
    """Parse output of ``git status --porcelain=v1 -z``.

    Format per entry (NUL-delimited):
        XY<SPACE>path<NUL>               # regular file (XY + space + path)
        XY<SPACE>new<NUL>old<NUL>        # rename/copy (XY + space + new path, then old path)

    Note: in the ``-z`` format git reverses the rename field order shown in the
    human format (``from -> to`` becomes ``to`` ``from``) and omits the score.
    """
    if not raw:
        return []

    entries: list[FileStatus] = []
    parts = raw.split("\0")

    i = 0
    while i < len(parts):
        part = parts[i]
        if not part:
            i += 1
            continue
        if len(part) < 4:  # Minimum: XY + space + at least 1 char for path
            i += 1
            continue

        index_status = part[0]
        worktree_status = part[1]

        path = part[3:]  # Skip XY (2 chars) + space (1 char); for renames this is the new path

        if index_status in ("R", "C"):
            i = _parse_rename_entry(parts, i, index_status, worktree_status, path, entries)
        else:
            i += 1
            entries.append(FileStatus(
                index_status=index_status,
                worktree_status=worktree_status,
                path=path,
                old_path=None,
            ))

    return entries


def _parse_rename_entry(
    parts: list[str],
    i: int,
    index_status: str,
    worktree_status: str,
    new_path: str,
    entries: list[FileStatus],
) -> int:
    """Parse a rename/copy entry, append it to ``entries``, and return the next index."""
    # ``new_path`` is the destination; the next part holds the old (source) path.
    i += 1
    old_path = parts[i] if i < len(parts) else ""
    i += 1
    entries.append(FileStatus(
        index_status=index_status,
        worktree_status=worktree_status,
        path=new_path,
        old_path=old_path,
    ))
    return i


def parse_push_output(raw: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Parse output of ``git push --porcelain``.

    Returns (ok_refs, failed_refs).
    """
    ok_refs: list[str] = []
    failed_refs: list[tuple[str, str]] = []

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("ok "):
            ok_refs.append(line[3:])
        elif line.startswith("ng "):
            parts = line[3:].split(" ", 1)
            ref = parts[0] if parts else ""
            reason = parts[1] if len(parts) > 1 else "unknown"
            failed_refs.append((ref, reason))

    return ok_refs, failed_refs
