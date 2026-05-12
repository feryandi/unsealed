import io
from pathlib import Path
from typing import Optional

from ...assets.blob import Blob
from ...utils.file import File


class SealTextureDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.filename: str = path.stem
    self.file: Optional[File] = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open texture file")

    self.grigon_header: Optional[bytes] = None
    self.original_file_size: Optional[int] = None
    self.scrambled_header: Optional[bytes] = None
    self.file_type: Optional[str] = None
    self.file_content: Optional[bytes] = None
    self.decoded: Optional[bytes] = None

  def decode(self) -> Blob:
    if self.file is None:
      raise Exception("File was not initialized properly")

    self.grigon_header = self.file.read(16 * 4)
    self.original_file_size = self.file.read_int()
    self.scrambled_header = self.file.read(18)
    self.file_type = self.__predict_filetype()
    self.file_content = self.file.seek_at(16 * 4 + 4, self.original_file_size)
    self.decoded = (self.__get_file_decoded()).getvalue()

    blob = Blob()
    blob.value = self.decoded
    blob.extension = self.file_type if self.file_type != "unknown" else None
    return blob

  def __get_file_decoded(self) -> io.BytesIO:
    assert self.file_content is not None, "File was not initialized properly"
    file_bytes = io.BytesIO()
    key = self.__key(self.file_content[0], self.file_type)
    for x in range(18):
      c = bytes([self.file_content[x] ^ key])
      file_bytes.write(c)
    file_bytes.write(self.file_content[18:])
    return file_bytes

  def __key(self, x: int, filetype: Optional[str]) -> int:
    if filetype == "dds":
      return x ^ 0x44
    if filetype == "jpg":
      return x ^ 0xFF
    if filetype == "bmp":
      return x ^ 0x42
    if filetype == "tga":
      return x ^ 0x00
    return 0

  def __predict_filetype(self) -> Optional[str]:
    assert self.file is not None, "File was not initialized properly"
    header_zero = 16 * 4 + 4

    check = self.file.seek_at(self.file.size - 18 - 16 * 4, 18)
    if (
      check
      == b"\x54\x52\x55\x45\x56\x49\x53\x49\x4f\x4e\x2d\x58\x46\x49\x4c\x45\x2e\x00"
    ):
      return "tga"

    check = self.file.seek_at(header_zero, 3)
    op = check[0] ^ 0x44
    if check[1] ^ op == 0x44 and check[2] ^ op == 0x53:
      return "dds"

    check_header = self.file.seek_at(header_zero, 3)
    op = check_header[0] ^ 0xFF
    check_footer = self.file.seek_at(self.file.size - 2 - 16 * 4, 2)
    if (
      check_header[1] ^ op == 0xD8
      and check_header[2] ^ op == 0xFF
      and check_footer == b"\xff\xd9"
    ):
      return "jpg"

    check = self.file.seek_at(header_zero, 2)
    op = check[0] ^ 0x42
    if check[1] ^ op == 0x4D:
      return "bmp"

    return None
