from typing import Any, Dict, List

from ..core.asset import Asset


class ItemDb(Asset):
  """A decoded Seal Online item-database shard (`.ed1`, `.ed2`, …).

  Each `.ed<n>` is an EDT-encrypted file (same LCG cipher as `.edt`)
  whose plaintext is a flat list of item records — NOT the `Seal Online
  ...File` header the `.dat` decoders expect, which is why it decodes to
  a bespoke item-db form. `n` matches the item-id band (`.ed1` holds
  ids 1000-1999, `.ed13` holds 13000-13317, …).

  `format` is "item-db" for the modern variable-length records (real
  item data) or "legacy" for the older fixed-size placeholder shards
  (`.ed14`-`.ed17`: id-only reserved slots).
  """

  def __init__(self) -> None:
    super().__init__()
    self.source_name: str = ""  # full source filename (e.g. "item.ed1")
    self.format: str = "item-db"
    self.items: List[Dict[str, Any]] = []

  def __repr__(self) -> str:
    return f"<ItemDb {self.source_name!r} {self.format} items:{len(self.items)}>"
