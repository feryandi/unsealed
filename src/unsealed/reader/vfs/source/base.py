"""FileSource — the protocol for where a Resource's bytes come from.

Implementations are siblings in this package: DiskSource (disk.py, a
real directory of loose files), SpakSource (spak.py, mounted .spak
archives decrypted on demand), and MemorySource (memory.py, an in-RAM
name->bytes map). All expose the same read/exists/resolve/list API so
decoders are agnostic to the origin.

Logical names are forward-slash and matched leniently: resolve is the
one place case-insensitivity + fallback lookups live, so callers never
re-implement them.
"""

from __future__ import annotations

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
