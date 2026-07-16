from typing import Union

from ...assets.tsv import Tsv
from ...utils.file import File
from ... import schemas as _schemas  # noqa: F401  (registers every schema)
from ..celltable import load_cell_table
from ..records import RecordSchema


class SealTsvDecoder:
  """Decode a Seal Online `.tsv` (tab-delimited text) into a Tsv asset.

  Same shape as `.scr` but tab-delimited and header-less (the `id` is the
  first column). `#` comments and blanks skipped; tokens stay raw and a
  schema types them. Pass `schema` (a name or RecordSchema) to produce
  labelled `records`.
  """

  DELIMITER = "\t"

  def __init__(self, file: File) -> None:
    self.file: File = file

  def decode(self, schema: Union[str, RecordSchema, None] = None) -> Tsv:
    return load_cell_table(Tsv(), self.file.data, self.DELIMITER, schema, "tsv")
