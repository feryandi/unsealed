"""Decode a Seal Online `.xml` data table into an `Xml` cell table.

Seal ships some data tables as XML (the pet `bpet*` family, produced by
decrypting the matching `.edt`). They are all the same shape: a root
element naming the table, then a flat list of `<item .../>` children whose
attributes are the columns. The schema is therefore EMBEDDED in the file
-- the attribute names -- so this decoder derives the columns from the
data rather than from the shared `REGISTRY`, and populates the same
`CellTable` fields (`rows`/`records`) the `.scr`/`.tsv` decoders do.

A document with no element children (a config-style XML) is not a table:
`is_table` is False and the raw text is kept as `strings`.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import List, Union

from ...assets.xml import Xml
from ...utils.file import File
from ..celltable import decode_text

# Column key for an element's own text content, used only when a child
# carries text between its tags (this keeps a stray text-bearing table
# from silently dropping data).
_TEXT_KEY = "#text"


def _coerce(token: str) -> Union[int, float, str]:
  """Type an attribute string like the cell decoders do: an integer when
  it round-trips exactly (so `"007"` stays a string, not `7`), then a
  float, else the raw string."""
  text = token.strip()
  if not text:
    return token
  if re.fullmatch(r"-?[0-9]+", text) and str(int(text)) == text:
    return int(text)
  try:
    return float(text)
  except ValueError:
    return token


class SealXmlDecoder:
  """Decode a Seal `.xml` table (bytes) into an `Xml` asset."""

  def __init__(self, file: File) -> None:
    self.file: File = file

  def decode(self) -> Xml:
    asset = Xml()
    asset.text = decode_text(self.file.data)
    asset.lines = asset.text.splitlines()

    try:
      root = ET.fromstring(asset.text)
    except ET.ParseError:
      # Not well-formed XML -- keep the text, but it's not a table.
      asset.is_table = False
      asset.strings = [ln for ln in asset.lines if ln.strip()]
      return asset

    asset.root_tag = root.tag
    children = list(root)
    if not children:
      # A leaf/config document, not a row table.
      asset.is_table = False
      asset.strings = [ln for ln in asset.lines if ln.strip()]
      return asset

    columns: List[str] = []
    parsed = []
    for child in children:
      fields = dict(child.attrib)
      text = (child.text or "").strip()
      if text:
        fields[_TEXT_KEY] = text
      for key in fields:
        if key not in columns:
          columns.append(key)
      parsed.append(fields)

    asset.schema_name = root.tag
    asset.columns = columns
    asset.records = [{k: _coerce(v) for k, v in fields.items()} for fields in parsed]
    # Raw token rows aligned to the column order, mirroring a `.scr`/`.tsv`
    # `rows` parse (the grid's fallback view and parity with the base type).
    asset.rows = [[fields.get(col, "") for col in columns] for fields in parsed]
    return asset
