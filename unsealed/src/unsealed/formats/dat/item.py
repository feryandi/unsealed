"""ItemDataFile body decoder.

Layout (v4), after the shared 64-byte header + int32 count (records
start at offset 68 — unlike MonsterDataFile there is no extra int):

    record[count]:
        block        176 bytes: a null-terminated EUC-KR name at the
                     start, followed by numeric int32 fields
        description  null-terminated EUC-KR string (variable length)

Records are variable-length (the description varies); the grammar walks
exactly `count` records to EOF. `id` is the row index (record 0 is a
placeholder named "a"). The numeric fields in the block are not mapped
yet — name + description are extracted; fields can be labelled later.
"""

from ...assets.dat import DatFile
from ...utils.file import File
from .registry import DatBody, register

_BLOCK = 176


def _kr(data: bytes) -> str:
  """Decode a Seal string, trying EUC-KR then western fallbacks."""
  for enc in ("euc_kr", "cp1252", "utf-8"):
    try:
      return data.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return data.decode("latin-1", "replace")


def _read_cstr(file: File) -> bytes:
  buf = bytearray()
  while True:
    ch = file.read(1)
    if not ch or ch == b"\x00":
      break
    buf += ch
  return bytes(buf)


class ItemDataBody(DatBody):
  type_name = "Seal Online ItemFile"
  versions = (4,)

  def decode(self, file: File, dat: DatFile) -> None:
    items = []
    for idx in range(dat.count):
      block = file.read(_BLOCK)
      name = _kr(block.split(b"\x00", 1)[0])
      description = _kr(_read_cstr(file))
      items.append({"id": idx, "name": name, "description": description})
    dat.elements = items


register(ItemDataBody())
