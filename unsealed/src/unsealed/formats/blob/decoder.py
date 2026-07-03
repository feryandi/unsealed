from pathlib import PurePosixPath

from ...assets.blob import Blob
from ...utils.file import File


class BlobDecoder:
  def __init__(self, file: File) -> None:
    self.file: File = file

  def decode(self) -> Blob:
    blob = Blob()
    blob.value = self.file.read_until_end()
    blob.extension = ".".join(self.file.suffixes)
    name = PurePosixPath(self.file.name)
    while name.suffix:
      name = name.with_suffix("")
    blob.name = name.name

    return blob
