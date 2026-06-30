from typing import Any, Dict, List, Optional, Union

from ..core.asset import Asset


class Scr(Asset):
  """A decoded Seal Online `.scr` script/config (plain text).

  `.scr` payloads are line-based text with varied per-file schemas. This
  keeps the raw `text`/`lines`, the leading `headers` (non-row lines),
  and a `rows` parse for the pipe-delimited table form. When a schema is
  applied, `records` holds the labelled rows and `header_values` the
  named header lines; both are empty otherwise.
  """

  def __init__(self) -> None:
    super().__init__()
    self.name: str = ""
    self.text: str = ""
    self.lines: List[str] = []
    self.headers: List[str] = []  # leading non-row (no-pipe) lines
    # Pipe-delimited data rows, cells parsed to int where possible.
    self.rows: List[List[Union[int, str]]] = []
    # Schema-applied results (empty unless a schema was given).
    self.schema_name: Optional[str] = None
    self.header_values: Dict[str, Any] = {}
    self.records: List[Dict[str, Any]] = []

  def __repr__(self) -> str:
    return f"<Scr {self.name!r} lines:{len(self.lines)} rows:{len(self.rows)}>"
