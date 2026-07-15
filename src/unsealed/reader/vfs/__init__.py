"""Virtual filesystem: read game files from disk or a mounted .spak.

Decoders/pipelines take a Resource (a Path-like handle) and read bytes
through a FileSource. The FileSource implementations live in vfs.source:
DiskSource serves loose files, SpakSource serves encrypted archive
entries (decrypted on demand), and MemorySource serves an in-RAM map —
mirroring how the game client mounts archives.
"""

from .resource import Resource
from .source import DiskSource, FileSource, MemorySource, SpakSource

__all__ = ["Resource", "FileSource", "DiskSource", "SpakSource", "MemorySource"]
