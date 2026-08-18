"""The byte substrate for record schemas: `.dat`'s leaf `FieldType`s.

A `.dat` record is a sequence of typed fields. Two things describe it:

  * a `FieldType` -- HOW to read one value (unnamed): scalars (`I32`,
    `U32`, `F32`, `I64`, `U64`, `F64`), strings (`Str(n)` fixed / `Cstr`
    null-terminated / `Pstr` `[len][bytes]`), and `Array(element)`
    (`[count][count x element]`). Types compose: `Array(Pstr)`,
    `Array(Array(F32))`, `Array(Str(40))`.
  * a `Column` -- a NAMED field in a record = `Column(name, FieldType)`.

A `RecordSchema` is an ordered tuple of `Column`s (+ optional typed
`headers` for the file-level int32s after `count`, such as the
`field_count` most types declare there, and an `index_field` to store the
row idx).
`read_record(file)` reads one record: if every column is fixed-width it
bulk-reads the row's int32 cells and carves them (fast path for the big
tables); otherwise it streams field-by-field (needed for `Pstr`/`Array`).

This module is one of the three schema substrate modules under `formats/`,
and the byte one:

  * `records.py` -- the substrate-agnostic core (`Column`, `Array`,
    `RecordSchema`, `read_record`, `REGISTRY`, `register_schema`).
  * `bytefields.py` (here) -- the `.dat` byte leaves + `generic_schema`.
  * `celltable.py` -- the `.scr`/`.tsv` cell leaf + cursor.

The concrete schemas themselves live in `reader/schemas/` and import their
whole vocabulary from here: the core's `Column` / `RecordSchema` / `I32` /
`register_schema` are re-exported below, so a `.dat` schema module needs
this one import.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from .records import Array, Column, Struct  # noqa: F401  (re-exported for schemas)
from .records import F32, I32, U32  # noqa: F401  (shared scalars, re-exported)
from .records import FieldType, RecordSchema  # noqa: F401  (byte leaf base + re-exported)
from .records import register_schema  # noqa: F401  (single registration entry, re-exported)


def _kr(raw: bytes) -> str:
  """Decode an EUC-KR byte run (western fallbacks); caller trims nulls."""
  for enc in ("euc_kr", "cp1252", "utf-8"):
    try:
      return raw.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return raw.decode("latin-1", "replace")


# `FieldType` is the byte-backed leaf for `.dat`: it reads one value
# straight from the file bytes and, for fixed-width types, can also carve
# it from pre-read int32 cells (`from_cells`, the fast path). The
# structural pieces -- `Column`, `Array`, `Struct`, `RecordSchema` and
# `read_record` -- are shared with `.scr` in `records.py`; here we only
# define the byte leaves. `read(cursor, record)` takes the file as its
# cursor and ignores `record` (only `Array` uses it).


@dataclass(frozen=True)
class _I64(FieldType):
  cells = 2

  def read(self, cursor, record=None):
    return struct.unpack("<q", cursor.read(8))[0]

  def from_cells(self, cells):
    raw = (cells[0] & 0xFFFFFFFF) | ((cells[1] & 0xFFFFFFFF) << 32)
    return raw - (1 << 64) if raw >= (1 << 63) else raw


@dataclass(frozen=True)
class _U64(FieldType):
  cells = 2

  def read(self, cursor, record=None):
    return struct.unpack("<Q", cursor.read(8))[0]

  def from_cells(self, cells):
    return (cells[0] & 0xFFFFFFFF) | ((cells[1] & 0xFFFFFFFF) << 32)


@dataclass(frozen=True)
class _F64(FieldType):
  cells = 2

  def read(self, cursor, record=None):
    return struct.unpack("<d", cursor.read(8))[0]

  def from_cells(self, cells):
    return struct.unpack(
      "<d", struct.pack("<II", cells[0] & 0xFFFFFFFF, cells[1] & 0xFFFFFFFF)
    )[0]


@dataclass(frozen=True)
class Str(FieldType):
  """Fixed-length EUC-KR string of `size` bytes, read up to the first null
  (trailing DB-dump garbage is dropped). `size` is usually a multiple of 4
  (the byte fast path carves it from whole int32 cells); an off-alignment
  size (e.g. `skill.py`'s 255-byte name buffer) just opts that column out
  of the fast path -- `cells` is None, so `RecordSchema` streams the whole
  record field-by-field instead, which reads any size correctly."""

  size: int

  @property
  def cells(self) -> Optional[int]:
    if self.size <= 0:
      raise ValueError("Str size must be a positive number of bytes")
    return self.size // 4 if self.size % 4 == 0 else None

  def read(self, cursor, record=None):
    return _kr(cursor.read(self.size).split(b"\x00", 1)[0])

  def from_cells(self, cells):
    return _kr(struct.pack(f"<{len(cells)}i", *cells).split(b"\x00", 1)[0])


@dataclass(frozen=True)
class _Cstr(FieldType):
  """Null-terminated EUC-KR string (variable length)."""

  cells = None

  def read(self, cursor, record=None):
    return _kr(cursor.read_cstring())


@dataclass(frozen=True)
class _Pstr(FieldType):
  """Length-prefixed EUC-KR string: [int32 len][len bytes]. The declared
  length often includes a trailing null terminator, so the value is cut
  at the first null (an all-null buffer reads as an empty string).

  A length that can't be satisfied raises rather than reading short. It
  means the cursor is misaligned -- the wrong schema, or a corrupt file
  -- and a silent short read hides that: the bogus length swallows the
  rest of the buffer, so the reader lands exactly on EOF and a caller
  probing "did this layout fit?" (`formats/edt/band.py`) is told yes.
  Raising lets the probe fail and fall back.
  """

  cells = None

  def read(self, cursor, record=None):
    n = cursor.read_int()
    if n <= 0:
      if n < 0:
        raise ValueError(f"Pstr: negative length {n}")
      return ""  # 0 is a legitimately empty string
    raw = cursor.read(n)
    if len(raw) != n:
      raise ValueError(f"Pstr: declared {n} bytes, {len(raw)} left")
    return _kr(raw.split(b"\x00", 1)[0])


# Singletons for the byte-only zero-argument types (`I32`/`U32`/`F32` are
# the shared scalars imported from `records.py`; parameterised ones are
# `Str(n)` / `Array(t)`). Use directly: Column("hp", I64), Column("desc", Pstr).
I64, U64, F64 = _I64(), _U64(), _F64()
Cstr, Pstr = _Cstr(), _Pstr()


# The placeholder layout for an untagged `Seal Online Data` file: a uniform
# grid of `width` plain int32 columns, so it still decodes to named rows
# (`field_0..field_N`) even when no schema is registered for its filename.
@lru_cache(maxsize=None)
def generic_schema(width: int) -> RecordSchema:
  """Placeholder schema of `width` plain int32 columns (field_0...), for
  untagged `Seal Online Data` files so they still decode to named rows."""
  return RecordSchema(
    name="generic", columns=tuple(Column(f"field_{i}", I32) for i in range(width))
  )
