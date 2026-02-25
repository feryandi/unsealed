from pathlib import Path
from typing import Optional

from ...utils.file import File


class SealMatDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.file: Optional[File] = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open mat file")

  def decode(self) -> None:
    """
    Decodes the MAT file
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    _header = self.file.read(44)

    _materials = []
    _textures = []

    while self.file.is_end() is False:
      _t = self.file.read_short()
      _name = self.file.read_string(256)
      _filename = self.file.read_string(256)

      _ = self.file.read(4)
      _material_ambient = [
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
      ]
      _second_four = [
        self.file.read_int(),
        self.file.read_int(),
        self.file.read_int(),
        self.file.read_int(),
      ]
      _x = self.file.read_int()
      _material_specular = [
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
      ]
      _x = self.file.read_int()
      _third_four = [
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
      ]
      _x = self.file.read_float()
      self.file.read(1)
