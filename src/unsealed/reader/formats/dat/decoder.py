import re

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

    title = self.raw[:_HEADER_LEN].split(b"\x00", 1)[0]
    title_str = title.decode("latin-1", "ignore").strip()
    m = _TITLE.match(title_str)
    if m:
      dat.type_name = m.group("type").strip()
      dat.version = _parse_version(m.group("ver"))
    else:
      dat.type_name = title_str
      dat.unknown["header"] = title_str

    file = File(self.raw)
    file.read(_HEADER_LEN)  # skip the 64-byte header
    dat.count = file.read_int()  # int32 element count

    body = for_type(dat.type_name, dat.version)
    if body is not None:
      # `file` is positioned just past the count; the body reads any
      # type-specific extra header then the records into `dat`.
      body.decode(file, dat)

    return dat
