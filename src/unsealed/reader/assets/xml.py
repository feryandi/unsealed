from typing import List

from .celltable import CellTable


class Xml(CellTable):
  """A decoded Seal Online `.xml` data table (e.g. the `bpet*` tables).

  These are self-describing tables: the root element names the table and
  each direct child (`<item .../>`) is one record whose attributes are the
  columns. Unlike `.scr`/`.tsv`, the schema is EMBEDDED in the file, so
  there is no `REGISTRY` lookup -- `columns` holds the ordered union of the
  child attribute names and `records` the labelled (type-coerced) rows.
  """

  def __init__(self) -> None:
    super().__init__()
    self.root_tag: str = ""  # the root element name (== the table type)
    self.columns: List[str] = []  # ordered attribute names (the schema)
