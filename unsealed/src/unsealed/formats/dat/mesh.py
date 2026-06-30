"""Mon_Grapic body decoder — the monster graphic / model table.

Layout (v2), after the shared 64-byte header + int32 count (records
start at offset 68 — like ItemFile there is NO extra int):

    record[count]:
        slot   36 bytes: a null-terminated model name at the start,
               followed by uninitialised DB-dump garbage

Each 36-byte slot maps a *graphic id* (the 0-based record index) to a
monster model base name, e.g. index 1 -> "T_By", index 2 -> "T_gr1". The
model's actor file is `<name>.act`.

`MonsterDataFile` (`monster.py`) references this table through its
model field (field[38]), so e.g. monster ids 1/2/3 all carry model
id 1 -> the "T_By" graphic here.

Only the leading name is meaningful: the rest of every slot holds
leftover bytes from a database export ("soft][ODBC ...", ",;.?\"0.0\"",
"Native:-1305,Origin:[Micro", "...xls - ReadE", a trailing 4-null gap),
which the game never cleared. We keep only the model name and drop the
garbage tail.
"""

from ...assets.dat import DatFile
from ...utils.file import File
from .registry import DatBody, register

_SLOT = 36


def _kr(data: bytes) -> str:
  """Decode a Seal string, trying EUC-KR then western fallbacks."""
  for enc in ("euc_kr", "cp1252", "utf-8"):
    try:
      return data.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return data.decode("latin-1", "replace")


class MonGrapicBody(DatBody):
  type_name = "Seal Online Mon_Grapic File"
  versions = (2,)

  def decode(self, file: File, dat: DatFile) -> None:
    elements = []
    for idx in range(dat.count):
      slot = file.read(_SLOT)
      # The model name is the leading null-terminated string; everything
      # after the first NUL is uninitialised DB-dump garbage.
      name = _kr(slot.split(b"\x00", 1)[0]).strip()
      elements.append(
        {
          "id": idx,  # graphic / model id (referenced by monster.dat)
          "model": name,
          "act": f"{name}.act" if name else "",
        }
      )
    dat.elements = elements


register(MonGrapicBody())
