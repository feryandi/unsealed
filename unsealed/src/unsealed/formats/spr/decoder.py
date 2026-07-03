from typing import List, Tuple

from ...utils.file import File


class SealSprDecoder:
  def __init__(self, file: File) -> None:
    self.file: File = file

  def decode(self) -> List[Tuple[str, List[Tuple[int, int, int, int]]]]:
    """Decode the SPR into a list of (filename, quads) tuples."""
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
