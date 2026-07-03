from .celltable import CellTable


class Tsv(CellTable):
  """A decoded Seal Online `.tsv` -- a tab-delimited `CellTable`
  (guarder/polymorph/...); a generic TSV with an `id` first column."""
