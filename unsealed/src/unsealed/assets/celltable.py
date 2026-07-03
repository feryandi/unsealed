from typing import Any, Dict, List, Optional

from ..core.asset import Asset


class CellTable(Asset):
  """A decoded line-based delimited Seal table (`.scr` pipe / `.tsv` tab).

  Keeps the raw `text`/`lines`, the leading `headers` (non-row lines), and
  a `rows` parse (raw tokens; a schema types them on demand). When a
  schema is applied, `records` holds the labelled rows and `header_values`
  the named header lines; both are empty otherwise.

  Not every such file is a table: some are plain line lists (e.g.
  `slang.scr`). When the leading lines are not the integer counts a table
  starts with, `is_table` is False and the content is exposed as `strings`
  (no `headers`/`rows`/schema applied).
  """

  def __init__(self) -> None:
    super().__init__()
    self.name: str = ""
    self.text: str = ""
    self.lines: List[str] = []
    self.is_table: bool = True  # False = plain string list, not a table
    self.strings: List[str] = []  # content lines when not a table
    self.headers: List[str] = []  # leading non-row (no-delimiter) lines
    self.rows: List[List[str]] = []  # data rows as RAW tokens
    # Schema-applied results (empty unless a schema was given).
    self.schema_name: Optional[str] = None
    self.header_values: Dict[str, Any] = {}
    self.records: List[Dict[str, Any]] = []

  def __repr__(self) -> str:
    return f"<{type(self).__name__} {self.name!r} lines:{len(self.lines)} rows:{len(self.rows)}>"
