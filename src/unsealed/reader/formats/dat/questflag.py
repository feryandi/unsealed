"""QuestFlagFile body decoder.

Layout (v1), after the shared 64-byte header + int32 count (records
start at offset 68 — there is NO extra header int):

    record[count]:
        int32   id          quest id (referenced elsewhere; NOT the
                            row index — non-sequential, range ~1..928)
        title   40 bytes    null-terminated EUC-KR quest title, then
                            uninitialised DB-dump garbage in the slot
        int32   stages      number of description blocks that follow
        description[stages]  each 256 bytes: null-terminated EUC-KR
                            text (a quest stage), zero/garbage padded

`stages` varies per quest (0..4 in the sample): 0 = a flag with a
title but no description text, >1 = a multi-stage / "child" quest whose
stages are stored back-to-back. The grammar walks exactly `count`
records to EOF.

Only the leading string of each fixed slot is meaningful; the tail of
the title slot holds leftover DB-export bytes (",;.?", etc.) which we
drop by splitting on the first NUL.
"""

from ...assets.dat import DatFile
from ...utils.file import File
from .registry import DatBody, register

_TITLE = 40
_DESC = 256


def _kr(data: bytes) -> str:
  """Decode the leading null-terminated string of a fixed slot."""
  data = data.split(b"\x00", 1)[0]
  for enc in ("euc_kr", "cp1252", "utf-8"):
    try:
      return data.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return data.decode("latin-1", "replace")


class QuestFlagBody(DatBody):
  type_name = "Seal Online QuestFlagFile"
  versions = (1,)

  def decode(self, file: File, dat: DatFile) -> None:
    quests = []
    for _ in range(dat.count):
      quest_id = file.read_int()
      title = _kr(file.read(_TITLE))
      stages = file.read_int()
      descriptions = [_kr(file.read(_DESC)) for _ in range(stages)]
      quests.append(
        {
          "id": quest_id,
          "title": title,
          "descriptions": descriptions,
        }
      )
    dat.elements = quests


register(QuestFlagBody())
