"""Virtual filesystem: read game files from disk or a mounted .spak.

Decoders/pipelines take a Resource (a Path-like handle) and read bytes
through a FileSource. DiskSource serves loose files; SpakSource
(vfs.spak_source) serves encrypted archive entries, decrypted on demand
— mirroring how the game client mounts archives.
"""

from .resource import Resource
from .source import DiskSource, FileSource

__all__ = ["Resource", "FileSource", "DiskSource"]
