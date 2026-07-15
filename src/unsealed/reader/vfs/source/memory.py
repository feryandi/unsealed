"""MemorySource — a FileSource over in-memory {name: bytes} entries.

Backs archives decoded eagerly into RAM (e.g. a `.mdt`), so their
members open through the same `Resource` path as loose files and `.spak`
entries: mount every member into one source, then hand out
`Resource(source, name)` per member. Sibling lookups between members
(a `.ms1` reaching for its `.bn1`/`.tex`) resolve within the same
source, mirroring how a `.spak` mounts its whole index.

Unlike SpakSource there's no decrypt-on-demand or shared file handle:
the bytes are already in hand, so read() is a plain dict lookup.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Dict, List, Optional


class MemorySource:
  """A FileSource backed by an in-memory mapping of name -> bytes."""

  def __init__(self, entries: Dict[str, bytes], label: str = "archive") -> None:
    self._entries: Dict[str, bytes] = {
      str(name).replace("\\", "/"): bytes(data) for name, data in entries.items()
    }
    # Lowercased index for case-insensitive resolve; first insert wins
    # so a primary-cased name isn't shadowed by a later collision.
    self._by_lower: Dict[str, str] = {}
    for name in self._entries:
      self._by_lower.setdefault(name.lower(), name)
    self.label = label

  def resolve(self, name: str) -> Optional[str]:
    name = name.replace("\\", "/")
    if name in self._entries:
      return name
    return self._by_lower.get(name.lower())

  def read(self, name: str) -> bytes:
    resolved = self.resolve(name)
    if resolved is None:
      raise FileNotFoundError(name)
    return self._entries[resolved]

  def exists(self, name: str) -> bool:
    return self.resolve(name) is not None

  def list(self, suffix: Optional[str] = None) -> List[str]:
    suf = suffix.lower() if suffix else None
    return [
      name
      for name in self._entries
      if suf is None or PurePosixPath(name).suffix.lower() == suf
    ]

  def __repr__(self) -> str:
    return f"<MemorySource {self.label} ({len(self._entries)} entries)>"
