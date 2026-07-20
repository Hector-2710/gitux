"""Utilities for parsing git porcelain output."""

from gitz.domain import FileStatus


def parse_status(raw: str) -> list[FileStatus]:
    """Parse output of ``git status --porcelain=v1 -z``.

    Format per entry (NUL-delimited):
        XY<SPACE>path<NUL>               # regular file (XY + space + path)
        R<SCORE><SPACE>old<NUL>new<NUL>  # rename/copy (XY + score + space + old, then new)
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

        path = part[3:]  # Skip XY (2 chars) + space (1 char)

        if index_status in ("R", "C"):
            if not path:  # Empty path means score wasn't separated
                i += 1
                continue
            score_end = path.find(" ")
            if score_end >= 0:
                old_path = path[score_end + 1:]
            else:
                old_path = path
            # Next part is new_path
            i += 1
            new_path = parts[i] if i < len(parts) else ""
            i += 1
            entries.append(FileStatus(
                index_status=index_status,
                worktree_status=worktree_status,
                path=new_path,
                old_path=old_path,
            ))
        else:
            i += 1
            entries.append(FileStatus(
                index_status=index_status,
                worktree_status=worktree_status,
                path=path,
                old_path=None,
            ))

    return entries


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
