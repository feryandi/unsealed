from pathlib import Path
from typing import Any, Dict, Optional

from ...utils.file import File


class SealSfxDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.file: Optional[File] = None
    self.unknown: Dict[str, Any] = {}
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

    self.unknown["header_68"] = self.file.read(68)

    entries = []
    while not self.file.is_end():
      entry: Dict[str, Any] = {}
      entry["filename"] = self.file.read_string(256)
      entry["name"] = self.file.read_string(256)

      entry["floats_7"] = [self.file.read_float() for _ in range(7)]
      entry["shorts_4"] = [self.file.read_short() for _ in range(4)]

      entry["byte_a"] = self.file.read(1)
      entry["floats_2_a"] = [self.file.read_float(), self.file.read_float()]
      entry["byte_b"] = self.file.read(1)

      entry["floats_6"] = [self.file.read_float() for _ in range(6)]

      # Empty, usually
      entry["pad_104"] = self.file.read(104)
      # Empty, usually
      entry["tail_string"] = self.file.read_string(256)

      entries.append(entry)
    self.unknown["entries"] = entries
