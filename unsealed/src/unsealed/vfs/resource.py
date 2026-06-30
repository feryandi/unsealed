"""Resource — a Path-like handle to a file inside a FileSource.

A Resource pairs a FileSource (a real dir or a mounted SPAK) with a
logical name and exposes the subset of the pathlib API decoders use
(name/stem/suffix/suffixes/with_suffix/with_name). Reads go through the
source, so the same decoder code works for disk files and archive
entries.

The pathlib-mirroring properties operate on the *leaf* of the logical
name (Resource("a/b.ms1").name == "b.ms1", like Path); the full logical
name used to address the source is kept internally.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
  from pathlib import Path

  from .source import FileSource


class Resource:
  __slots__ = ("source", "_name")

  def __init__(self, source: "FileSource", name: str) -> None:
    self.source = source
    self._name = str(name).replace("\\", "/")

  # ── pathlib-mirroring API (operates on the logical name) ──

  @property
  def name(self) -> str:
    return PurePosixPath(self._name).name

  @property
  def stem(self) -> str:
    return PurePosixPath(self._name).stem

  @property
  def suffix(self) -> str:
    return PurePosixPath(self._name).suffix

  @property
  def suffixes(self) -> List[str]:
    return PurePosixPath(self._name).suffixes

  def with_suffix(self, suffix: str) -> "Resource":
    return Resource(self.source, str(PurePosixPath(self._name).with_suffix(suffix)))

  def with_name(self, new_name: str) -> "Resource":
    return Resource(self.source, str(PurePosixPath(self._name).with_name(new_name)))

  def sibling(self, new_name: str) -> "Resource":
    """Alias of with_name — a file beside this one in the source."""
    return self.with_name(new_name)

  # ── source-backed IO ──

  @property
  def logical_name(self) -> str:
    """Full forward-slash name of this file within its source."""
    return self._name

  @property
  def disk_path(self) -> "Optional[Path]":
    """The real on-disk path, when backed by a DiskSource (else None).

    Used by consumers that need a true filesystem path (e.g. opening a
    .spak via zipfile) rather than going through read().
    """
    from .source import DiskSource

    if isinstance(self.source, DiskSource):
      return self.source.root / self._name
    return None

  def read(self) -> bytes:
    return self.source.read(self._name)

  def exists(self) -> bool:
    return self.source.resolve(self._name) is not None

  @classmethod
  def for_disk_file(cls, path: "Path") -> "Resource":
    """Wrap a loose on-disk file (root = its parent directory)."""
    from .source import DiskSource

    return cls(DiskSource(path.parent), path.name)

  def __repr__(self) -> str:
    return f"<Resource {self._name!r} @ {self.source!r}>"
