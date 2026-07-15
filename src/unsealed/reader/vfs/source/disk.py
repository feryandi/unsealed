"""DiskSource — a FileSource over a directory of loose files."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import List, Optional


class DiskSource:
  """A FileSource backed by a real directory of loose files."""

  def __init__(self, root: Path) -> None:
    self.root = Path(root)

  def resolve(self, name: str) -> Optional[str]:
    name = name.replace("\\", "/")
    if (self.root / name).is_file():
      return name
    # Case-insensitive fallback for the leaf within its dir (mirrors the
    # old sprite_atlas / _find_object_file iterdir lookups).
    rel = PurePosixPath(name)
    parent = self.root / rel.parent
    if parent.is_dir():
      target = rel.name.lower()
      for entry in parent.iterdir():
        if entry.is_file() and entry.name.lower() == target:
          if str(rel.parent) == ".":
            return entry.name
          return f"{rel.parent}/{entry.name}"
    return None

  def read(self, name: str) -> bytes:
    resolved = self.resolve(name)
    if resolved is None:
      raise FileNotFoundError(name)
    return (self.root / resolved).read_bytes()

  def exists(self, name: str) -> bool:
    return self.resolve(name) is not None

  def list(self, suffix: Optional[str] = None) -> List[str]:
    if not self.root.is_dir():
      return []
    suf = suffix.lower() if suffix else None
    return [
      e.name
      for e in self.root.iterdir()
      if e.is_file() and (suf is None or e.suffix.lower() == suf)
    ]

  def __repr__(self) -> str:
    return f"<DiskSource {self.root}>"
