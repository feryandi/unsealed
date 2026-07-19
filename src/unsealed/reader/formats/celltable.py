"""Shared machinery for line-based delimited tables.

Two Seal text formats are the same thing with a different cell delimiter:
`.scr` (pipe `|` -- npc/m/drop/warp) and `.tsv` (tab -- guarder/polymorph).
Both are "leading integer header lines, then delimited data rows", read
through the shared `RecordSchema`/`read_record` (see `records.py`) with a
`CellCursor` over each row's raw tokens. This module owns everything the
two share; `formats/scr/` and `formats/tsv/` only pick the delimiter and
register their own schemas.

A file that does NOT open with integer metadata is not a table at all but a
plain line list (e.g. `slang.scr`, a word filter); `load_cell_table` flags
that via `is_table=False` and keeps the lines as `strings`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from .records import (
  Array,
  Column,
  FieldType,
  Fill,
  FromField,
  I32,
  REGISTRY,
  RecordSchema,
  Struct,
)

# A raw token is text until a `Column` type reads it; the labelled value is
# whatever that type produces (int for `I32`, str for `Text`, ...).
Cell = Union[int, str]


# -- cell leaf + cursor ----------------------------------------------------


@dataclass(frozen=True)
class _Text(FieldType):
  """A text cell -- the raw token as a string (None if absent). The cell
  analogue of a `.dat` byte string; used for columns that hold a name
  (e.g. the guarder model column)."""

  cells = None

  def read(self, cursor: "CellCursor", record=None) -> Optional[str]:
    return cursor.read_text()


Text = _Text()


class CellCursor:
  """A record-bounded cursor over one row's raw tokens (or the header
  lines). Typed reads mirror a byte cursor's -- `read_int` parses the next
  token as an int, etc. -- so the shared leaf types work unchanged.
  Exposes `remaining`/`drain` (what `Array`'s `Fill` and `read_record`'s
  `_extra` probe for); a byte cursor instead exposes `read_ints`."""

  def __init__(self, tokens: List[str]) -> None:
    self._tokens = tokens
    self._pos = 0

  def _next(self) -> Optional[str]:
    if self._pos >= len(self._tokens):
      return None
    tok = self._tokens[self._pos]
    self._pos += 1
    return tok

  def read_int(self) -> Optional[int]:
    # A missing / blank / non-integer ("junk") token reads as None -- an
    # absent value, not a fabricated 0. Some tables leave an integer slot
    # empty or carry corruption in their 0-padded tails (e.g. a stray
    # `0.05` where an item id belongs); typing stays strict (no int/str
    # guessing) but a single junk cell never aborts the whole table.
    tok = self._next()
    if tok is None or not tok.strip():
      return None
    try:
      return int(tok)
    except ValueError:
      return None

  def read_uint(self) -> Optional[int]:
    val = self.read_int()
    return None if val is None else val & 0xFFFFFFFF

  def read_float(self) -> Optional[float]:
    tok = self._next()
    if tok is None or not tok.strip():
      return None
    try:
      return float(tok)
    except ValueError:
      return None

  def read_text(self) -> Optional[str]:
    return self._next()

  def remaining(self) -> int:
    return len(self._tokens) - self._pos

  def drain(self) -> List[str]:
    """Consume and return whatever is left in the row (surfaces as the
    record's `_extra`)."""
    rest = self._tokens[self._pos :]
    self._pos = len(self._tokens)
    return rest


# -- schema-building shorthands (produce plain typed `Column`s) ------------


def i32s(*names: str) -> Tuple[Column, ...]:
  """A run of int columns."""
  return tuple(Column(n, I32) for n in names)


def group(
  name: str, fields: Tuple[str, ...], count_field: Optional[str] = None
) -> Column:
  """A trailing repeating group: `Array` of a `Struct` of int fields,
  sized by a prior `count_field` column, or fill-to-end when None."""
  element = Struct(i32s(*fields))
  count = FromField(count_field) if count_field is not None else Fill()
  return Column(name, Array(element, count=count))


def apply_headers(schema: RecordSchema, lines: List[str]) -> Dict[str, Cell]:
  """Read the leading single-value lines through the schema's typed
  `headers` columns (one token per line, same leaf types as the rows)."""
  cursor = CellCursor(lines)
  return {col.name: col.type.read(cursor, {}) for col in schema.headers}


# -- decoding --------------------------------------------------------------


def decode_text(data: bytes) -> str:
  for enc in ("euc_kr", "cp1252", "utf-8"):
    try:
      return data.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return data.decode("latin-1", "replace")


def _is_int(token: str) -> bool:
  try:
    int(token)
    return True
  except ValueError:
    return False


def _is_table(header_lines: List[str], rows: List[List[str]]) -> bool:
  """A table opens with integer metadata (a row/element count). Probe the
  first couple of leading lines: if they are not ints the file is a plain
  line list (e.g. `slang.scr`), not a table. With no leading lines, it is
  a table only if it has delimited rows."""
  probe = header_lines[:2]
  if probe:
    return all(_is_int(line) for line in probe)
  return bool(rows)


def _partition(
  text: str, delimiter: str
) -> Tuple[List[str], List[str], List[List[str]], List[str]]:
  """Split text into (all lines, leading header lines, delimited rows as
  raw tokens, non-blank content lines). `#` comments and blanks skipped."""
  lines = text.splitlines()
  header_lines: List[str] = []
  rows: List[List[str]] = []
  content: List[str] = []
  seen_row = False
  for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
      continue
    content.append(stripped)
    # A leading count line may carry a trailing delimiter (`buffdesc` opens
    # `511|`, unlike drop/npc's bare `3588`). Before any real row, a line
    # that is a single integer once trailing delimiters are stripped is a
    # header, not a one-cell row -- otherwise the count leaks in as record 0.
    body = stripped.rstrip(delimiter)
    if not seen_row and delimiter not in body and _is_int(body):
      header_lines.append(body)
      continue
    if delimiter in line:
      rows.append(line.rstrip(delimiter).split(delimiter))
      seen_row = True
    elif not seen_row:
      header_lines.append(stripped)
  return lines, header_lines, rows, content


def load_cell_table(asset, raw: bytes, delimiter: str, schema, fmt: str):
  """Populate `asset` (a `CellTable`) from `raw` bytes. Non-table files
  (no integer header) keep their content as `strings`; tables split into
  `headers`/`rows` and, when a schema resolves, labelled `records`. A
  schema name is resolved against the shared `REGISTRY` scoped to `fmt`
  ("scr"/"tsv"); a `RecordSchema` is used as-is."""
  asset.text = decode_text(raw)
  lines, header_lines, rows, content = _partition(asset.text, delimiter)
  asset.lines = lines

  if not _is_table(header_lines, rows):
    asset.is_table = False
    asset.strings = content
    return asset

  asset.headers = header_lines
  asset.rows = rows
  sch = REGISTRY.get(fmt, schema)
  if sch is not None:
    asset.schema_name = sch.name
    asset.header_values = apply_headers(sch, asset.headers)
    asset.records = [
      sch.read_record(CellCursor(row), i) for i, row in enumerate(asset.rows)
    ]
  return asset
