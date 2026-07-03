from pathlib import Path, PurePosixPath

from ...assets.blob import Blob
from ...assets.directory import Directory
from ...assets.spak import SpakArchive


class SpakDecoder:
  """Decodes a Seal Online .spak archive into a Directory of Blobs.

  Reads every entry. The password is derived deterministically from the
  format version in the zip's global comment ("Seal Online Zip v<V>").
  """

  def __init__(self, path: Path) -> None:
    self.path: Path = path

  def decode(self) -> Directory:
    with SpakArchive(self.path) as archive:
      directory = Directory(name=self.path.stem)
      for info in archive.infos:
        directory.list.append(self._to_blob(info.filename, archive.read(info)))
    return directory

  @staticmethod
  def _to_blob(filename: str, content: bytes) -> Blob:
    name = SpakArchive._normalize(filename)
    pure = PurePosixPath(name)
    blob = Blob()
    blob.value = content
    blob.extension = pure.suffix.lstrip(".") or None
    # Keep any sub-directory prefix so the layout can be reproduced.
    blob.name = name[: -len(pure.suffix)] if pure.suffix else name
    return blob
