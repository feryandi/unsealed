from pathlib import Path
from typing import Optional

from ...assets.blob import Blob
from ...utils.file import File


class BlobDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.file: Optional[File] = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open texture file")

  def decode(self) -> Blob:
    if self.file is None:
      raise Exception("File was not initialized properly")

    blob = Blob()
    blob.value = self.file.read_until_end()
    blob.extension = str.join(".", self.path.suffixes)
    blob.filename = self.path.with_suffix("").name
    while self.path.suffix:
      path = self.path.with_suffix("")
    blob.filename = path.name

    return blob
