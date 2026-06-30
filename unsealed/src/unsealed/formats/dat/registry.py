"""Registry of per-type/version `.dat` body decoders.

The shared header (type + version) and the int32 element count are read
by `SealDatDecoder`; decoding the actual records is delegated to a
`DatBody` registered for that type+version. The body receives the File
positioned just past the count, so it can also read any type-specific
extra header fields (e.g. MonsterDataFile has one extra int32 there).

To add support for a new file type, in a new module under this package:

    import struct
    from .registry import DatBody, register

    class MonsterDataBody(DatBody):
      type_name = "SealOnline MonsterDataFile"
      versions = (12,)            # () = any version

      def decode(self, file, dat):
        dat.unknown["extra"] = file.read_int()  # type-specific header
        rec = struct.Struct("<64i")
        dat.elements = [
          rec.unpack(file.read(256)) for _ in range(dat.count)
        ]

    register(MonsterDataBody())

then import the module in `formats/dat/__init__.py` so it registers.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Tuple

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


_BODIES: List[DatBody] = []


def register(body: DatBody) -> None:
  _BODIES.append(body)


def for_type(type_name: str, version: int) -> Optional[DatBody]:
  """The registered body for this type+version, or None if unhandled."""
  for body in _BODIES:
    if body.handles(type_name, version):
      return body
  return None
