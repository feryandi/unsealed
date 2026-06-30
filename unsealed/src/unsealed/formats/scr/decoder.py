from typing import Optional, Union

from ...assets.scr import Scr
from ...utils.file import FileLike, _read_bytes
from .schema import ScrSchema, get_schema, parse_cell


def _decode_text(data: bytes) -> str:
  for enc in ("euc_kr", "cp1252", "utf-8"):
    try:
      return data.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return data.decode("latin-1", "replace")


class SealScrDecoder:
  """Decode a Seal Online `.scr` (line-based text) into a Scr asset.

  Splits into leading `headers` (non-pipe lines) and pipe-delimited
  `rows` of cells (ints where possible); `#` comments and blanks are
  skipped. Pass `schema` (a name or ScrSchema) to also produce labelled
  `records` + `header_values`.
  """

  def __init__(self, path: FileLike) -> None:
    self.path: FileLike = path
    try:
      self.raw: bytes = _read_bytes(path)
    except Exception:
      raise Exception(f"Unable to open scr file: {path}")

  def decode(self, schema: Union[str, ScrSchema, None] = None) -> Scr:
    scr = Scr()
    scr.text = _decode_text(self.raw)
    scr.lines = scr.text.splitlines()

    seen_row = False
    for line in scr.lines:
      stripped = line.strip()
      if not stripped or stripped.startswith("#"):
        continue
      if "|" in line:
        scr.rows.append([parse_cell(c) for c in line.rstrip("|").split("|")])
        seen_row = True
      elif not seen_row:
        scr.headers.append(stripped)  # leading metadata line

    sch: Optional[ScrSchema] = get_schema(schema)
    if sch is not None:
      scr.schema_name = sch.name
      scr.header_values = sch.apply_headers(scr.headers)
      scr.records = [sch.apply_row(row, i) for i, row in enumerate(scr.rows)]
    return scr
