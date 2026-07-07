"""FileSource — where a Resource's bytes come from.

Two implementations exist: DiskSource (a real directory of loose files)
and SpakSource (mounted .spak archives, decrypt-on-demand; lives in
vfs/spak_source.py). Both expose the same read/exists/resolve/list API
so decoders are agnostic to the origin.

Logical names are forward-slash and matched leniently: resolve is the
one place case-insensitivity + fallback lookups live, so callers never
re-implement them.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import List, Optional, Protocol, runtime_checkable


@runtime_checkable
class FileSource(Protocol):
  def read(self, name: str) -> bytes:
    """Return the bytes of *name*; raise FileNotFoundError if absent."""
    ...

  def exists(self, name: str) -> bool: ...

  def resolve(self, name: str) -> Optional[str]:
    """Canonical stored name for *name*, or None if it doesn't exist."""
    ...

  def list(self, suffix: Optional[str] = None) -> List[str]:
    """All entry names, optionally filtered by *suffix*."""
    ...


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
