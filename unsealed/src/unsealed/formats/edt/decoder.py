from pathlib import Path

from ...assets.edt import Edt
from .codec import decode


class EdtDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    try:
      with open(path, "rb") as dat:
        self.raw: bytes = dat.read()
    except Exception:
      raise Exception(f"Unable to open edt file: {path}")

  def decode(self) -> Edt:
    edt = Edt()
    edt.value = decode(self.raw)
    edt.name = self.path.stem
    return edt
