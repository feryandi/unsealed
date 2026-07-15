import re
from typing import Optional, Tuple

from ...assets.dat import DatFile
from ...utils.file import File
from .registry import for_type

_HEADER_LEN = 64

# The header title: a type name followed by " v<number>", e.g.
# "SealOnline MonsterDataFile v12" or "Seal Online ItemFile v4". Matched
# as a prefix (not anchored at end) and non-greedily, so the version is
# the first " v<num>" right after the type name — any binary that
# follows the title within the 64-byte header is ignored.
_TITLE = re.compile(r"^(?P<type>.*?)\s+v(?P<ver>[0-9A-Fa-f]+)")


def _parse_version(token: str) -> int:
  """Parse the version token after 'v' (decimal first, then hex)."""
  for base in (10, 16):
    try:
      return int(token, base)
    except ValueError:
      continue
  return 0


def parse_header(raw: bytes) -> Tuple[str, Optional[int]]:
  """`(type_name, version)` from a `.dat`'s 64-byte header title.

  `version` is None when the title carries no ` v<num>` — the caller
  decides whether that's fatal. Only the first 64 bytes are read, so a
  caller holding just the header prefix can identify a file without
  decoding it (see `formats/edt/band.py`).
  """
  title = raw[:_HEADER_LEN].split(b"\x00", 1)[0].decode("latin-1", "ignore").strip()
  match = _TITLE.match(title)
  if not match:
    return title, None
  return match.group("type").strip(), _parse_version(match.group("ver"))


class SealDatDecoder:
  """Decode a Seal Online `.dat`: shared header + count, then dispatch
  the records to the body decoder registered for this type+version."""

  def __init__(self, file: File) -> None:
    self.file: File = file
    self.raw: bytes = file.data

  def decode(self) -> DatFile:
    dat = DatFile()
    dat.source_name = self.file.stem
    if len(self.raw) < _HEADER_LEN + 4:
      raise Exception("Not a valid .dat file (shorter than header + count)")

    type_name, version = parse_header(self.raw)
    dat.type_name = type_name
    if version is None:  # no " v<num>" in the title: keep it verbatim
      dat.unknown["header"] = type_name
    else:
      dat.version = version

    file = File(self.raw)
    file.read(_HEADER_LEN)  # skip the 64-byte header
    dat.count = file.read_int()  # int32 element count

    body = for_type(dat.type_name, dat.version)
    if body is not None:
      # `file` is positioned just past the count; the body reads any
      # type-specific extra header then the records into `dat`.
      body.decode(file, dat)

    return dat
