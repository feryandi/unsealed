from ...assets.edt import Edt
from ...utils.file import FileLike, _read_bytes
from .classify import detect_extension
from .codec import decode


class EdtDecoder:
  def __init__(self, path: FileLike) -> None:
    self.path: FileLike = path
    try:
      self.raw: bytes = _read_bytes(path)
    except Exception:
      raise Exception(f"Unable to open edt file: {path}")

  def decode(self) -> Edt:
    edt = Edt()
    edt.value = decode(self.raw)
    edt.name = self.path.stem
    edt.extension = detect_extension(edt.value)
    return edt
