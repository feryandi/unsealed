from pathlib import Path
from typing import Optional

from ...utils.file import File


class SealSfxDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.file: Optional[File] = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open sfx file")

  def decode(self) -> None:
    """
    Decodes the SFX file
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    _unknown = self.file.read(68)

    while self.file.is_end() is False:
      _filename = self.file.read_string(256)
      _name = self.file.read_string(256)

      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()

      _ = self.file.read_short()
      _ = self.file.read_short()
      _ = self.file.read_short()
      _ = self.file.read_short()

      _ = self.file.read(1)
      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read(1)

      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()
      _ = self.file.read_float()

      _ = self.file.read(104)  # Empty, usually
      _ = self.file.read_string(256)  # Empty, usually
