from pathlib import Path
from typing import List, Optional, Tuple

from ...assets.blob import Blob
from ...assets.directory import Directory
from ...utils.file import File


class SealMdtDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.file: Optional[File] = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open mdt file")

  def decode(self) -> Directory:
    """
    Decodes the MDT file and returns a list of blob: (filename, data_bytes)
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    num_files = self.file.read_int()

    file_metadata: List[Tuple[str, int]] = []
    for _ in range(num_files):
      filename = self.file.read_string(16 * 6)
      _ = self.file.read(4)
      size = self.file.read_int()
      _ = self.file.read(4)  # Skip the start offset pointer
      file_metadata.append((filename, size))

    decoded_files = []
    for filename, size in file_metadata:
      # Read the actual byte data from the stream
      blob = Blob()
      blob.value = self.file.read(size)
      parts = filename.split(".", 1)
      blob.filename = parts[0]
      blob.extension = parts[1] if len(parts) > 1 else None
      decoded_files.append(blob)

    dir = Directory()
    dir.list = decoded_files
    return dir
