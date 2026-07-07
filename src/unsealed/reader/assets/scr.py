from .celltable import CellTable


class Scr(CellTable):
  """A decoded Seal Online `.scr` script/config -- a pipe-delimited
  `CellTable` (npc/m/drop/warp), or a plain line list when not a table."""
