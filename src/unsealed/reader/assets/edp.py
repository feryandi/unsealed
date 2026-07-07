from typing import Any, Dict, List

from ..core.asset import Asset


class EdpArchive(Asset):
  """A decoded Seal Online `.edp` item package (e.g. `item_pak.edp`).

  A two-layer LCG-ciphered container that bundles every item-db shard
  into one file. Both cipher layers are the same generator as `.edt`;
  see `formats/edp/decoder.py` for the header/block passes and directory
  layout. Members are the item-id-band shards (`ITEM.ED1`..`ITEM.ED13`)
  plus a single `ITEM.EDT` (a "Seal Online ItemFile v10" `.dat`).

  Each entry in `members` is `{name, format, count, items}` where `items`
  is the parsed item-record list for that member.
  """

  def __init__(self) -> None:
    super().__init__()
    self.source_name: str = ""  # full source filename (e.g. "item_pak.edp")
    self.members: List[Dict[str, Any]] = []

  def __repr__(self) -> str:
    return f"<EdpArchive {self.source_name!r} members:{len(self.members)}>"
