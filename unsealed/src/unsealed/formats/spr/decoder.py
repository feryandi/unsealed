from typing import List, Optional, Tuple

from ...utils.file import File, FileLike


class SealSprDecoder:
  def __init__(self, path: FileLike) -> None:
    self.path: FileLike = path
    self.file: Optional[File] = None
    try:
      self.file = File(path)
    except Exception:
      raise Exception("Unable to open spr file")

  def decode(self) -> List[Tuple[str, List[Tuple[int, int, int, int]]]]:
    """Decode the SPR into a list of (filename, quads) tuples."""
    if self.file is None:
      raise Exception("File was not initialized properly")

    num_files = self.file.read_int()

    file_metadata = []
    for _ in range(num_files):
      filename = self.file.read_string(200)
      count = self.file.read_int()
      quads = []
      for _ in range(count):
        a = self.file.read_int()
        b = self.file.read_int()
        c = self.file.read_int()
        d = self.file.read_int()
        quads.append((a, b, c, d))

      file_metadata.append((filename, quads))

    return file_metadata
