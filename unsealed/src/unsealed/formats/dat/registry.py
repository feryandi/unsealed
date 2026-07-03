"""Registry of per-type/version `.dat` body decoders.

The shared header (type + version) and the int32 element count are read
by `SealDatDecoder`; decoding the actual records is delegated to a
`DatBody` registered for that type+version. The body receives the File
positioned just past the count, so it can also read any type-specific
extra header fields (e.g. MonsterDataFile has one extra int32 there).

To add support for a new file type, in a new module under this package:

    from .registry import DatBody, register

    class MonsterDataBody(DatBody):
      type_name = "SealOnline MonsterDataFile"
      versions = (12,)            # () = any version

      def decode(self, file, dat):
        dat.unknown["extra"] = file.read_int()  # type-specific header
        dat.elements = [
          file.read_ints(64) for _ in range(dat.count)  # 64 int32 / record
        ]

    register(MonsterDataBody())

then import the module in `formats/dat/__init__.py` so it registers.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Tuple

from ..records import REGISTRY

if TYPE_CHECKING:
  from ...assets.dat import DatFile
  from ...utils.file import File


def normalize_type(name: str) -> str:
  """Canonical key for a title (case/whitespace-insensitive)."""
  return re.sub(r"\s+", "", name).lower()


class DatBody(ABC):
  """Decodes the records for one .dat type+version family."""

  type_name: str = ""  # title, e.g. "SealOnline MonsterDataFile"
  versions: Tuple[int, ...] = ()  # supported versions; () means any

  def handles(self, type_name: str, version: int) -> bool:
    if normalize_type(type_name) != normalize_type(self.type_name):
      return False
    return not self.versions or version in self.versions

  @abstractmethod
  def decode(self, file: "File", dat: "DatFile") -> None:
    """Populate `dat.elements` from `file`.

    `file` is positioned just past the int32 count; the body may first
    read type-specific extra header fields (storing them in
    `dat.unknown`). `dat.count` / `dat.version` are already set.
    """
    ...


class SchemaBody(DatBody):
  """A `DatBody` that decodes a self-describing `.dat` type from a
  declarative `DataSchema` instead of bespoke code. Reads `header_extra`
  int32s after the count (stored in `dat.unknown`), then walks the
  records via `schema.read_record`.

  The schema is not held by a registered body -- it lives in the shared
  `REGISTRY` (registered by `schemas/dat/`), and `for_type` builds a
  `SchemaBody` around it on demand. Normally exactly `count` records are
  read; a schema with `until_eof=True` (its header `count` is a GLOBAL
  total while the file holds only a leading band, e.g. ItemFile v10) is
  walked to EOF and the header count kept in `unknown["declared_count"]`.
  """

  _MIN_RECORD = 8  # smallest sane trailing record (id + one length/int)

  def __init__(self, schema) -> None:
    self.schema = schema

  def decode(self, file: "File", dat: "DatFile") -> None:
    if self.schema.header_extra:
      dat.unknown["header_extra"] = [
        file.read_int() for _ in range(self.schema.header_extra)
      ]
    dat.unknown["schema"] = self.schema.name
    if self.schema.until_eof:
      records = []
      while not file.is_end() and file.size - file.pointer >= self._MIN_RECORD:
        records.append(self.schema.read_record(file, len(records)))
      dat.unknown["declared_count"] = dat.count
      dat.elements = records
    else:
      dat.elements = [self.schema.read_record(file, i) for i in range(dat.count)]


_BODIES: List[DatBody] = []


def register(body: DatBody) -> None:
  """Register a bespoke `DatBody` (e.g. `DataTableBody`, `QuestFlagBody`).
  Schema-driven types are NOT registered here -- they live in `REGISTRY`
  and are resolved by `for_type`."""
  _BODIES.append(body)


def for_type(type_name: str, version: int) -> Optional[DatBody]:
  """The body for this type+version, or None if unhandled. Bespoke bodies
  win; otherwise a schema registered under type dispatch (tag "dat") is
  wrapped in a `SchemaBody`."""
  for body in _BODIES:
    if body.handles(type_name, version):
      return body
  schema = REGISTRY.for_type("dat", type_name, version)
  if schema is not None:
    return SchemaBody(schema)
  return None
