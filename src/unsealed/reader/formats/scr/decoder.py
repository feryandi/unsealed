from typing import Union

from ...assets.scr import Scr
from ...utils.file import File
from ... import schemas as _schemas  # noqa: F401  (registers every schema)
from ..celltable import load_cell_table
from ..records import RecordSchema


class SealScrDecoder:
  """Decode a Seal Online `.scr` (pipe-delimited text) into a Scr asset.

  Splits into leading `headers` (non-pipe lines) and `|`-delimited `rows`
  of RAW tokens; `#` comments and blanks skipped. Typing is the schema's
  job -- pass `schema` (a name or RecordSchema) to produce labelled
  `records` + `header_values`. A file that is not a table (no integer
  header, e.g. a word list) is kept as `strings`.
  """

  DELIMITER = "|"

  def __init__(self, file: File) -> None:
    self.file: File = file

  def decode(self, schema: Union[str, RecordSchema, None] = None) -> Scr:
    return load_cell_table(Scr(), self.file.data, self.DELIMITER, schema, "scr")
