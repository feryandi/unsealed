"""Shared record-schema core for `.dat` (bytes) and `.scr`/`.tsv` (text cells).

All are "a table of records, each a sequence of named fields". They differ
only in the *substrate*: `.dat` records are packed binary read from a byte
stream, `.scr`/`.tsv` records are delimited tokens parsed from a line. This
module owns everything that does NOT depend on the substrate -- the shared
scalar leaves (`I32`/`U32`/`F32`), `Column`, `Struct`, `Array`,
`RecordSchema`, and `read_record` -- and reads through a `Cursor` so each
format supplies only its own extra leaf `FieldType`s and a matching cursor:

  * `.dat` -> a byte `Cursor` (`File`) + byte-only `FieldType`s (`I64`,
    `Str`, `Pstr`, ... in `bytefields.py`). It exposes `read_ints`, so
    an all-fixed record is bulk-read and carved in one shot (fast path).
  * `.scr`/`.tsv` -> a `CellCursor` over the row's tokens (+ a `Text` cell
    leaf, in `formats/celltable.py`). It exposes `drain`, so leftover
    tokens surface as `_extra`, and `remaining`, so a `Fill` group
    consumes to end of row.

A `Cursor` therefore isn't a strict interface; `read_record` probes for the
capabilities it needs (`read_ints` -> fast path, `drain` -> `_extra`) and a
cursor implements only the leaf reads its `FieldType`s actually call.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


class FieldType:
  """Reads one value from a `Cursor`. `cells` is the value's fixed width
  in int32 cells for the byte fast path, or None if it is variable-length
  / not byte-backed (then it must be stream-read via `read`)."""

  cells: Optional[int] = None

  def read(self, cursor: Any, record: Dict[str, Any]) -> Any:
    """Stream-read one value; `record` is the fields read so far in this
    record (used by `Array`'s `FromField` count)."""
    raise NotImplementedError

  def from_cells(self, cells: List[int]) -> Any:  # fixed byte types only
    raise NotImplementedError


# -- shared scalar leaf types ----------------------------------------------
#
# Substrate-neutral: each reads via a cursor method every cursor provides
# (`read_int` / `read_uint` / `read_float`), so the SAME `I32` / `F32`
# describe a 4-byte field in a `.dat` byte stream AND an integer token in a
# `.scr` row -- the leaf decides the type, the cursor decides the substrate.
# `from_cells` carves the value from pre-read int32 cells (the byte fast
# path); a cell cursor never calls it. Wider / byte-framed leaves (`I64`,
# `Str`, `Cstr`, `Pstr`, ...) are `.dat`-only and live in `bytefields.py`.


@dataclass(frozen=True)
class _I32(FieldType):
  cells = 1

  def read(self, cursor, record=None):
    return cursor.read_int()

  def from_cells(self, cells):
    return cells[0]


@dataclass(frozen=True)
class _U32(FieldType):
  cells = 1

  def read(self, cursor, record=None):
    return cursor.read_uint()

  def from_cells(self, cells):
    return cells[0] & 0xFFFFFFFF


@dataclass(frozen=True)
class _F32(FieldType):
  cells = 1

  def read(self, cursor, record=None):
    return cursor.read_float()

  def from_cells(self, cells):
    return struct.unpack("<f", struct.pack("<i", cells[0]))[0]


I32, U32, F32 = _I32(), _U32(), _F32()


# -- repeating-group count strategies --------------------------------------


class CountSpec:
  """How an `Array` learns how many elements to read."""


@dataclass(frozen=True)
class Inline(CountSpec):
  """The count is read from the source right before the elements: the
  `.dat` `[int32 count][count x element]` layout."""


@dataclass(frozen=True)
class FromField(CountSpec):
  """The count is the value of an earlier named column in this record --
  e.g. the `.scr` npc group whose length is a leading `count` column."""

  name: str


@dataclass(frozen=True)
class Fill(CountSpec):
  """Consume the rest of the record -- the `.scr` drop group that repeats
  to the end of the row. Only valid on a record-bounded cursor."""


# -- composite field types -------------------------------------------------


@dataclass(frozen=True)
class Struct(FieldType):
  """A fixed sub-record of named columns -- one element of an `Array`
  whose element is itself several fields (e.g. drop = `(item_id, rate)`)."""

  columns: Tuple["Column", ...]
  cells = None

  @property
  def width(self) -> int:
    """Cells/tokens one element consumes (used by `Fill`)."""
    return len(self.columns)

  def read(self, cursor, record=None):
    sub: Dict[str, Any] = {}
    for c in self.columns:
      sub[c.name] = c.type.read(cursor, sub)
    return sub


@dataclass(frozen=True)
class Array(FieldType):
  """A repeating group of `element`, its length set by `count`."""

  element: FieldType
  count: CountSpec = field(default_factory=Inline)
  cells = None

  @property
  def width(self) -> int:
    return getattr(self.element, "width", 1)

  def read(self, cursor, record=None):
    c = self.count
    if isinstance(c, FromField):
      n = (record or {}).get(c.name, 0)
      n = n if isinstance(n, int) else 0
    elif isinstance(c, Fill):
      n = cursor.remaining() // (self.width or 1)
    else:  # Inline: the count is read from the source (byte cursors)
      n = cursor.read_int()
    # On a record-bounded cursor (cells), never over-read past the row --
    # a short final element is dropped. A byte cursor has no `remaining`
    # and trusts its inline count exactly.
    remaining = getattr(cursor, "remaining", None)
    out: List[Any] = []
    for _ in range(max(n, 0)):
      if remaining is not None and remaining() < self.width:
        break
      out.append(self.element.read(cursor, {}))
    return out


@dataclass(frozen=True)
class Column:
  """A named field in a record."""

  name: str
  type: FieldType


@dataclass(frozen=True)
class RecordSchema:
  """An ordered tuple of `Column`s describing one record.

  `index_field` stores the row index under that name. `header_extra`
  (`.dat`) is a count of int32s to skip after the element count; `headers`
  (`.scr`) are typed `Column`s for the leading non-row lines (one value per
  line, e.g. `Column("row_count", I32)`); `until_eof` (`.dat`) walks records
  to end-of-file instead of trusting the header count (formats whose count
  is a global total but the file holds only a leading band, e.g. ItemFile
  v10) -- all three are consumed by the format's decoder, not by
  `read_record`.
  """

  name: str
  columns: Tuple[Column, ...] = ()
  index_field: Optional[str] = None
  header_extra: int = 0
  headers: Tuple[Column, ...] = ()
  until_eof: bool = False

  def __post_init__(self) -> None:
    fixed = all(c.type.cells is not None for c in self.columns)
    object.__setattr__(self, "_fixed", fixed)
    object.__setattr__(
      self, "_ncells", sum(c.type.cells for c in self.columns) if fixed else 0
    )

  @property
  def total_cells(self) -> Optional[int]:
    """Int32 cells per record, or None if the record is variable-length."""
    return self._ncells if self._fixed else None

  def read_record(self, cursor: Any, index: int = 0) -> Dict[str, Any]:
    rec: Dict[str, Any] = {}
    if self.index_field is not None:
      rec[self.index_field] = index
    read_ints = getattr(cursor, "read_ints", None)
    if self._fixed and read_ints is not None:  # byte fast path: bulk + carve
      cells = read_ints(self._ncells)
      pos = 0
      for c in self.columns:
        n = c.type.cells
        rec[c.name] = c.type.from_cells(cells[pos : pos + n])
        pos += n
    else:  # stream field by field (variable length, or a cell cursor)
      for c in self.columns:
        rec[c.name] = c.type.read(cursor, rec)
    drain = getattr(cursor, "drain", None)
    if drain is not None:  # record-bounded cursor: leftover tokens -> _extra
      leftover = drain()
      if leftover:
        rec["_extra"] = leftover
    return rec


# -- shared schema registry ------------------------------------------------
#
# One registry for ALL formats, so the schema *system* and its *catalogue*
# live together. Every schema is registered under a format tag (`fmt`:
# "dat" / "scr" / "tsv") and dispatched two ways -- by FILENAME pattern
# and/or by TYPE_NAME (the `.dat` header title) -- each optionally scoped
# to a set of versions. Lookups always take the `fmt` first, so a `.scr`
# and a `.dat` schema may share a name or an overlapping pattern without
# clashing. `.scr`/`.tsv` use only filename dispatch (no version/type).


def _normalize_type(name: str) -> str:
  """Canonical key for a type title (case/whitespace-insensitive)."""
  return re.sub(r"\s+", "", name).lower()


class SchemaRegistry:
  """Format-tagged catalogue of `RecordSchema`s (filename + type_name
  dispatch, version-aware). One shared instance, `REGISTRY`, holds every
  format's schemas; `formats/<fmt>` register into it and query it scoped
  to their own tag."""

  def __init__(self) -> None:
    # (fmt, schema name) -> schema
    self._schemas: Dict[Tuple[str, str], RecordSchema] = {}
    # (fmt, compiled filename pattern, accepted versions, schema name)
    self._filename_rules: List[Tuple[str, "re.Pattern[str]", Tuple[int, ...], str]] = []
    # (fmt, normalized type name, accepted versions, schema name)
    self._type_rules: List[Tuple[str, str, Tuple[int, ...], str]] = []

  def register(
    self,
    fmt: str,
    schema: RecordSchema,
    *,
    patterns: Tuple[str, ...] = (),
    type_names: Tuple[str, ...] = (),
    versions: Tuple[int, ...] = (),
  ) -> None:
    """Register `schema` under `fmt`, dispatched by any of `patterns`
    (filename) and/or `type_names` (`.dat` header title). `versions=()`
    means any version; versioned rules should precede agnostic ones for
    the same key (first match wins).

    A schema NAME must be unique within a format: registering a different
    schema under a `(fmt, name)` already taken is a bug (the catalogue is
    keyed by it), so it raises rather than silently overwriting."""
    key = (fmt, schema.name)
    existing = self._schemas.get(key)
    if existing is not None and existing is not schema:
      raise ValueError(f"duplicate schema name {schema.name!r} for format {fmt!r}")
    self._schemas[key] = schema
    for pat in patterns:
      self._filename_rules.append(
        (fmt, re.compile(pat, re.IGNORECASE), versions, schema.name)
      )
    for type_name in type_names:
      self._type_rules.append((fmt, _normalize_type(type_name), versions, schema.name))

  def get(
    self, fmt: str, schema: Union[str, RecordSchema, None]
  ) -> Optional[RecordSchema]:
    """Resolve a schema passed as a `RecordSchema` (returned as-is), a
    registered name (looked up within `fmt`), or None."""
    if isinstance(schema, RecordSchema):
      return schema
    if isinstance(schema, str):
      return self._schemas.get((fmt, schema))
    return None

  def for_filename(
    self, fmt: str, stem: str, version: Optional[int] = None
  ) -> Optional[RecordSchema]:
    """Filename+version lookup within `fmt`. Version-agnostic rules match
    any version; first matching rule wins."""
    for f, pat, versions, name in self._filename_rules:
      if f != fmt or not pat.search(stem):
        continue
      if versions and version not in versions:
        continue
      return self._schemas[(fmt, name)]
    return None

  def for_type(
    self, fmt: str, type_name: str, version: Optional[int] = None
  ) -> Optional[RecordSchema]:
    """Type_name+version lookup within `fmt` (the self-describing `.dat`
    types)."""
    key = _normalize_type(type_name)
    for f, typ, versions, name in self._type_rules:
      if f != fmt or typ != key:
        continue
      if versions and version not in versions:
        continue
      return self._schemas[(fmt, name)]
    return None

  def by_format(self, fmt: str) -> Dict[str, RecordSchema]:
    """`{name: schema}` snapshot of every schema registered under `fmt`
    (unified view for tooling / tests)."""
    return {name: sch for (f, name), sch in self._schemas.items() if f == fmt}

  def versions_for(self, fmt: str, name: str) -> Tuple[int, ...]:
    """Sorted union of the versions this schema is dispatched under
    (across its filename + type rules), or `()` if it's version-agnostic
    (any version). Lets tooling show which client version a schema
    targets."""
    versions: set = set()
    for f, _pat, vers, n in self._filename_rules:
      if f == fmt and n == name:
        versions.update(vers)
    for f, _typ, vers, n in self._type_rules:
      if f == fmt and n == name:
        versions.update(vers)
    return tuple(sorted(versions))


# The single shared registry every format registers into and queries.
REGISTRY = SchemaRegistry()


def register_schema(
  fmt: str,
  schema: RecordSchema,
  *,
  patterns: Tuple[str, ...] = (),
  type_names: Tuple[str, ...] = (),
  versions: Tuple[int, ...] = (),
) -> None:
  """The single registration entry point shared by every schema format
  (`.dat` / `.scr` / `.tsv`): register `schema` into `REGISTRY` under
  `fmt`, dispatched by filename `patterns` and/or `type_names`,
  optionally scoped to `versions` (`()` = any). Schema modules call this
  directly -- there are no per-format registration wrappers."""
  REGISTRY.register(
    fmt, schema, patterns=patterns, type_names=type_names, versions=versions
  )


def schema_for_filename(
  fmt: str, stem: str, version: Optional[int] = None
) -> Optional[RecordSchema]:
  """Filename+version schema lookup within `fmt` -- the read-side
  counterpart to `register_schema` (any version if unscoped)."""
  return REGISTRY.for_filename(fmt, stem, version)
