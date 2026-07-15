"""FileSource implementations: disk, .spak archive, and in-RAM.

The FileSource protocol (base.py) plus its three interchangeable
backends. Grouped so decoders can stay origin-agnostic and new sources
slot in beside these without touching the vfs surface.
"""

from .base import FileSource
from .disk import DiskSource
from .memory import MemorySource
from .spak import SpakSource

__all__ = ["FileSource", "DiskSource", "SpakSource", "MemorySource"]
