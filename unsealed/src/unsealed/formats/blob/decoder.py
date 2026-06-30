from typing import Optional

from ...assets.blob import Blob
from ...utils.file import File, FileLike


class BlobDecoder:
  def __init__(self, path: FileLike) -> None:
    self.path: FileLike = path
    self.file: Optional[File] = None
    try:
      self.file = File(path)
    except Exception:
      raise Exception("Unable to open texture file")

  def decode(self) -> Blob:
    if self.file is None:
      raise Exception("File was not initialized properly")

    blob = Blob()
    blob.value = self.file.read_until_end()
    blob.extension = ".".join(self.path.suffixes)
    path = self.path
    while path.suffix:
      path = path.with_suffix("")
    blob.name = path.name

    return blob
