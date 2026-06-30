"""SpakSource — a FileSource over mounted .spak archives.

Mounts the opened archive plus its sibling archives in the same install
(``<root>/*/*.SPAK``) as one virtual filesystem and decrypts entries on
demand into an in-memory cache — mirroring the game client. Nothing is
extracted to disk.

``read`` is guarded by a lock: SpakArchive shares a single file handle
and is not thread-safe, and the .spr atlas-decode pool calls ``read``
concurrently. The lock serializes archive IO; the expensive PIL decode
happens on the returned bytes, outside the lock.
"""

from __future__ import annotations

import threading
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

from ..formats.spak.decoder import SpakArchive


def _norm(name: str) -> str:
  return name.replace("\\", "/").lower()


class SpakSource:
  def __init__(self, spak_path: Path) -> None:
    self.path = spak_path
    self.primary = SpakArchive(spak_path)
    self.archives: List[SpakArchive] = [self.primary]
    self._open_siblings(spak_path)

    self._primary_names: List[str] = self.primary.names()
    # lowercased name -> (archive, cased name); the opened archive is
    # indexed first so it wins any cross-archive name collision.
    self._index: Dict[str, Tuple[SpakArchive, str]] = {}
    for arc in self.archives:
      for n in arc.names():
        self._index.setdefault(_norm(n), (arc, n))

    self._cache: Dict[str, bytes] = {}
    self._lock = threading.Lock()

  def _open_siblings(self, spak_path: Path) -> None:
    """Open the other ``<root>/*/*.SPAK`` archives (best-effort)."""
    primary = spak_path.resolve()
    root = primary.parent.parent
    if not root.is_dir():
      return
    for sp in sorted(root.glob("*/*.SPAK")):
      if sp.resolve() == primary:
        continue
      try:
        self.archives.append(SpakArchive(sp))
      except Exception as e:
        print(f"[spak] skip sibling {sp.name}: {e}")

  # ── FileSource API ──

  def resolve(self, name: str) -> Optional[str]:
    found = self._index.get(_norm(name))
    return found[1] if found is not None else None

  def exists(self, name: str) -> bool:
    return _norm(name) in self._index

  def read(self, name: str) -> bytes:
    key = _norm(name)
    found = self._index.get(key)
    if found is None:
      raise FileNotFoundError(name)
    arc, actual = found
    with self._lock:
      cached = self._cache.get(key)
      if cached is None:
        cached = arc.read(actual)
        self._cache[key] = cached
      return cached

  def list(self, suffix: Optional[str] = None) -> List[str]:
    suf = suffix.lower() if suffix else None
    return [
      cased
      for (_arc, cased) in self._index.values()
      if suf is None or PurePosixPath(cased).suffix.lower() == suf
    ]

  # ── extras ──

  def primary_names(self) -> List[str]:
    """Entry names of the opened archive only (for the file browser)."""
    return list(self._primary_names)

  def close(self) -> None:
    for arc in self.archives:
      try:
        arc.close()
      except Exception:
        pass

  def __repr__(self) -> str:
    return f"<SpakSource {self.path.name} (+{len(self.archives) - 1} siblings)>"
