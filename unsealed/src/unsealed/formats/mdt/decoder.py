from typing import Any, Dict, List, Optional, Tuple

from ...assets.blob import Blob
from ...assets.directory import Directory
from ...utils.file import File, FileLike


class SealMdtDecoder:
  def __init__(self, path: FileLike) -> None:
    self.path: FileLike = path
    self.file: Optional[File] = None
    self.unknown: Dict[str, Any] = {}
    try:
      self.file = File(path)
    except Exception:
      raise Exception("Unable to open mdt file")

  def decode(self) -> Directory:
    """Decode the MDT into a Directory of (filename, data) blobs."""
    if self.file is None:
      raise Exception("File was not initialized properly")

    num_files = self.file.read_int()

    file_metadata: List[Tuple[str, int]] = []
    pre_size_pads = []
    offset_pointers = []
    for _ in range(num_files):
      filename = self.file.read_string(16 * 6)
      pre_size_pads.append(self.file.read(4))
      size = self.file.read_int()
      offset_pointers.append(self.file.read(4))
      file_metadata.append((filename, size))
    self.unknown["pre_size_pads"] = pre_size_pads
    self.unknown["offset_pointers"] = offset_pointers

    decoded_files = []
    for filename, size in file_metadata:
      # Read the actual byte data from the stream
      blob = Blob()
      blob.value = self.file.read(size)
      parts = filename.split(".", 1)
      blob.name = parts[0]
      blob.extension = parts[1] if len(parts) > 1 else None
      decoded_files.append(blob)

    dir = Directory()
    dir.list = decoded_files
    return dir
