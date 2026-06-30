from typing import Any, Dict, List

from ..core.asset import Asset


class DatFile(Asset):
  """A decoded Seal Online `.dat` data file.

  `.dat` files share a 64-byte header whose first null-terminated string
  names the type + version (e.g. "SealOnline MonsterDataFile v12"),
  followed by an int32 element count and `count` type-specific records.

  `elements` is filled by the body decoder registered for this
  type+version (see `formats/dat/registry.py`); it stays empty when no
  decoder handles the file yet — the header + count are still available.
  """

  def __init__(self) -> None:
    super().__init__()
    self.type_name: str = ""  # title, e.g. "SealOnline MonsterDataFile"
    self.version: int = 0
    self.count: int = 0  # declared number of elements
    self.elements: List[Any] = []  # decoded records (type/version specific)
    self.unknown: Dict[str, Any] = {}

  def __repr__(self) -> str:
    return (
      f"<DatFile {self.type_name!r} v{self.version} "
      f"count:{self.count} elements:{len(self.elements)}>"
    )
