"""Surface tokens (V1) — the single source for colors used in Python renders.

The tcss mirrors these values (Textual CSS cannot import Python); keep both
in sync. One token per role — the strays (#34d399, #22c55e, #f59e0b,
#f87171, #e2e8f0, #64748b, #e4e1ed, #c7c4d7, #958ea0) are absorbed per
``ux/surface.md`` V1.
"""

TEXT = "#e6e0f1"            # the one text-white
TEXT_SECONDARY = "#cbc3d7"  # secondary text (absorbs #c7c4d7, #e2e8f0)
TEXT_DIM = "#908fa0"        # hints, placeholders (absorbs #64748b, #958ea0)

PURPLE_STRUCTURE = "#8B5CF6"  # structure: active borders
PURPLE_EMPHASIS = "#9c60ec"   # emphasis: cursor, titles, diff headers

GREEN = "#10b981"           # added / clean / sync-ok (absorbs #34d399, #22c55e)
AMBER = "#ffb783"           # modified / dirty / pending (absorbs #f59e0b)
RED = "#ffb4ab"             # deleted / error / conflict (absorbs #f87171)
CYAN = "#06B6D4"            # info: branch badge, staged, R/C states (quiet)

BG_BLOCK = "#0f0d18"        # block content background
BG_SURFACE = "#1c1a26"      # secondary surface
BG_INPUT = "#201e2a"        # input / badge background
BG_ADDITION = "#123a2a"     # diff addition tint
BG_DELETION = "#3a1d1d"     # diff deletion tint
LINE_NUM = "#4a3a6b"        # diff gutter
BG_ERROR = "#93000a"         # error container (detached HEAD, destructive)
