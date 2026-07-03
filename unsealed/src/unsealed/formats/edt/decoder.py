from ...assets.edt import Edt
from ...utils.file import File
from .classify import detect_extension
from .codec import decode


class EdtDecoder:
  def __init__(self, file: File) -> None:
    self.file: File = file

  def decode(self) -> Edt:
    edt = Edt()
    edt.value = decode(self.file.data)
    edt.name = self.file.stem
    edt.extension = detect_extension(edt.value)
    return edt
