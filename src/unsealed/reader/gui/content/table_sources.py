"""Table data sources for the schema-driven `.dat`/`.scr`/`.tsv` views.

A *source* turns one decoded file into a flat string grid under a chosen
schema, and offers the list of schemas the user may pick from. It's the
Qt-free half of the table feature — `table_view.py` renders whatever a
source produces and drives schema selection through it.

All three formats share the same `RecordSchema` machinery (see
`formats/records.py`): a `.dat` reads packed bytes, a `.scr`/`.tsv`
reads delimited tokens, but both end up as records of named fields. So a
source re-applies a schema to the file's raw units (byte stream / token
rows) and flattens the resulting records into strings.

The default schema is the one the decoders already pick (filename/type
regex); a schema is flagged *fitting* when its column count matches the
data, so the picker can hide the obviously-wrong ones by default.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

# Importing the schemas package registers every schema into REGISTRY.
from ...schemas import REGISTRY
from ...assets.celltable import CellTable
from ...assets.dat import DatFile
from ...assets.xml import Xml
from ...formats.celltable import CellCursor
from ...formats.dat.registry import SchemaBody, for_type
from ...formats.records import RecordSchema
from ...utils.file import File

# Cap rendered rows so a huge table (item shards) can't freeze the grid;
# the source notes when it truncated.
MAX_ROWS = 20000
# Cap a single rendered cell so a big nested group stays readable.
MAX_CELL = 300


@dataclass(frozen=True)
class SchemaOption:
  """One entry in the schema picker."""

  label: str
  fits: bool  # column count matches the data (else hidden unless "show all")
  version: str = ""  # client version(s) it targets, e.g. "v12" ("" = any)


def _version_label(fmt: str, name: str) -> str:
  """Display hint of the versions a schema is registered under, e.g.
  "v4/v10"; empty when the schema is version-agnostic."""
  versions = REGISTRY.versions_for(fmt, name)
  return "v" + "/".join(str(v) for v in versions) if versions else ""


@dataclass
class TableData:
  """A flat string grid ready for the model, plus a status note."""

  columns: List[str]
  rows: List[List[str]]
  note: str = ""
  truncated: bool = False


# -- cell / record flattening ---------------------------------------


def render_cell(value: Any) -> str:
  if value is None:
    return ""
  if isinstance(value, bool):
    return str(value)
  if isinstance(value, (int, float, str)):
    text = str(value)
  else:  # a nested group (Array/Struct) -> compact JSON
    try:
      text = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
      text = str(value)
  return text if len(text) <= MAX_CELL else text[: MAX_CELL - 1] + "…"


def _schema_columns(schema: RecordSchema, records: List[Any]) -> List[str]:
  names: List[str] = []
  if schema.index_field:
    names.append(schema.index_field)
  names += [c.name for c in schema.columns]
  if any(isinstance(r, dict) and "_extra" in r for r in records):
    names.append("_extra")
  return names


def _records_grid(records: List[Any], columns: List[str]) -> List[List[str]]:
  rows: List[List[str]] = []
  for rec in records[:MAX_ROWS]:
    if isinstance(rec, dict):
      rows.append([render_cell(rec.get(name)) for name in columns])
    elif isinstance(rec, (list, tuple)):
      cells = [render_cell(v) for v in rec]
      cells += [""] * (len(columns) - len(cells))
      rows.append(cells)
    else:
      rows.append([render_cell(rec)] + [""] * (len(columns) - 1))
  return rows


# -- adapters -------------------------------------------------------


class CellTableAdapter:
  """Schema source over a decoded `.scr`/`.tsv` (`CellTable`).

  The unit of data is a row of raw tokens (`asset.rows`); applying a
  schema re-reads those tokens through a `CellCursor`. A non-table file
  (a plain word list) has no rows, so only the raw view is offered.
  """

  RAW = "None — raw columns"

  def __init__(self, asset: CellTable, fmt: str, stem: str) -> None:
    self._asset = asset
    self._fmt = fmt
    self._rows = asset.rows
    self._schemas: Dict[str, RecordSchema] = REGISTRY.by_format(fmt)
    matched = REGISTRY.for_filename(fmt, stem)
    self._default = matched.name if (matched and self._rows) else self.RAW
    kind = fmt.upper()
    self.title = f"{asset.name or stem}  ·  {kind} table"

    sample = self._rows[:25]
    self._fits = {
      name: self._schema_fits(sch, sample) for name, sch in self._schemas.items()
    }

  @property
  def default_label(self) -> str:
    return self._default

  def options(self) -> List[SchemaOption]:
    opts = [SchemaOption(self.RAW, True)]
    for name in sorted(self._schemas):
      fits = self._fits.get(name, False) or name == self._default
      opts.append(SchemaOption(name, fits, _version_label(self._fmt, name)))
    return opts

  def apply(self, label: str) -> TableData:
    schema = self._schemas.get(label)
    if schema is None:
      return self._raw_grid()
    records = [
      schema.read_record(CellCursor(list(row)), i)
      for i, row in enumerate(self._rows[:MAX_ROWS])
    ]
    columns = _schema_columns(schema, records)
    rows = _records_grid(records, columns)
    return TableData(columns, rows, truncated=len(self._rows) > MAX_ROWS)

  def _raw_grid(self) -> TableData:
    if not self._rows and self._asset.strings:
      return TableData(["line"], [[s] for s in self._asset.strings[:MAX_ROWS]])
    width = max((len(r) for r in self._rows), default=0)
    columns = [f"col_{i}" for i in range(width)]
    rows: List[List[str]] = []
    for row in self._rows[:MAX_ROWS]:
      cells = [render_cell(v) for v in row]
      cells += [""] * (width - len(cells))
      rows.append(cells)
    return TableData(columns, rows, truncated=len(self._rows) > MAX_ROWS)

  @staticmethod
  def _schema_fits(schema: RecordSchema, sample: List[List[str]]) -> bool:
    """A schema fits when it consumes each sampled row cleanly: no
    leftover tokens (too few columns) and no empty fixed field (too
    many)."""
    if not sample:
      return True
    for row in sample:
      rec = schema.read_record(CellCursor(list(row)), 0)
      if rec.get("_extra"):
        return False
      for col in schema.columns:
        if col.type.cells is not None and rec.get(col.name) is None:
          return False
    return True


class XmlTableAdapter:
  """Schema source over a decoded `.xml` table (`Xml`).

  Unlike `.scr`/`.tsv`/`.dat`, the schema is EMBEDDED in the file (the
  `<item>` attribute names the decoder already extracted into
  `asset.columns`), so there is no `REGISTRY` lookup and a single option:
  the root tag. A non-table document (no `<item>` children) shows its raw
  lines instead.
  """

  def __init__(self, asset: Xml, stem: str) -> None:
    self._asset = asset
    self._label = asset.root_tag or "embedded"
    root = f"  ·  <{asset.root_tag}>" if asset.root_tag else ""
    self.title = f"{asset.name or stem}  ·  XML table{root}"

  @property
  def default_label(self) -> str:
    return self._label

  def options(self) -> List[SchemaOption]:
    return [SchemaOption(self._label, True)]

  def apply(self, label: str) -> TableData:
    if not self._asset.is_table:
      strings = self._asset.strings
      return TableData(["line"], [[s] for s in strings[:MAX_ROWS]])
    columns = list(self._asset.columns)
    records = self._asset.records
    rows = [
      [render_cell(rec.get(col)) for col in columns] for rec in records[:MAX_ROWS]
    ]
    return TableData(columns, rows, truncated=len(records) > MAX_ROWS)


class DatTableAdapter:
  """Schema source over a decoded `.dat` (`DatFile`).

  The unit of data is the packed byte record. "Auto" shows whatever the
  real decoder produced (its type-matched schema); picking another
  schema re-reads the raw bytes through a `SchemaBody`. A schema fits
  when its fixed record width matches the file's byte layout.

  `header_size` is how many bytes precede the first record: 68 for a
  `.dat` (the 64-byte header + the int32 count), but 0 for an `.ed<n>`
  item band, whose records start at offset 0 (see `formats/edt/band.py`).
  """

  AUTO = "Auto — decoded"
  DAT_HEADER = 64 + 4  # shared header + int32 element count

  def __init__(
    self,
    dat: DatFile,
    raw: bytes,
    stem: str,
    *,
    header_size: int = DAT_HEADER,
    suffix: str = ".dat",
  ) -> None:
    self._dat = dat
    self._raw = raw
    self._header_size = header_size
    self._schemas: Dict[str, RecordSchema] = REGISTRY.by_format("dat")
    label = f"{dat.type_name} v{dat.version}" if dat.type_name else "unknown type"
    self.title = f"{stem}{suffix}  ·  {label}"

    body = for_type(dat.type_name, dat.version)
    self._default = body.schema.name if isinstance(body, SchemaBody) else self.AUTO
    self._fits = {name: self._schema_fits(sch) for name, sch in self._schemas.items()}

  @property
  def default_label(self) -> str:
    return self._default

  def options(self) -> List[SchemaOption]:
    opts = [SchemaOption(self.AUTO, True)]
    for name in sorted(self._schemas):
      fits = self._fits.get(name, False) or name == self._default
      opts.append(SchemaOption(name, fits, _version_label("dat", name)))
    return opts

  def apply(self, label: str) -> TableData:
    if label == self.AUTO or label not in self._schemas:
      return self._auto_grid()
    schema = self._schemas[label]
    records = self._decode_with(schema)
    columns = _schema_columns(schema, records)
    rows = _records_grid(records, columns)
    return TableData(columns, rows, truncated=len(records) > MAX_ROWS)

  def _auto_grid(self) -> TableData:
    records = self._dat.elements
    if records and isinstance(records[0], dict):
      # Union of keys over a sample keeps late/optional fields visible.
      columns: List[str] = []
      for rec in records[:50]:
        for key in rec:
          if key not in columns:
            columns.append(key)
    elif records and isinstance(records[0], (list, tuple)):
      width = max(len(r) for r in records)
      columns = [f"field_{i}" for i in range(width)]
    else:
      columns = []
    rows = _records_grid(records, columns)
    return TableData(columns, rows, truncated=len(records) > MAX_ROWS)

  def _decode_with(self, schema: RecordSchema) -> List[Any]:
    file = File(self._raw)
    file.read(self._header_size)  # skip the header + count (0 for a band)
    scratch = DatFile()
    scratch.count = self._dat.count
    scratch.version = self._dat.version
    SchemaBody(schema).decode(file, scratch)
    return scratch.elements

  def _schema_fits(self, schema: RecordSchema) -> bool:
    total = schema.total_cells
    if total is None or self._dat.count <= 0:
      return False  # variable width or empty: can't cheaply verify
    region = len(self._raw) - self._header_size - 4 * schema.header_extra
    return region == self._dat.count * total * 4
