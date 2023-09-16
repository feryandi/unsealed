import io
import os

from file import File


class SealTextureFileDecoder:
  def __init__(self, path):
    self.path = path
    self.filename = os.path.splitext(os.path.basename(path))[0]
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except:
      raise Exception("Unable to open texture file")

    self.grigon_header = None
    self.original_file_size = None
    self.scrambled_header = None
    self.file_type = None
    self.file_content = None
    self.decoded = None

  def decode(self):
    self.grigon_header = self.file.read(16 * 4)
    self.original_file_size = self.file.read_int()
    self.scrambled_header = self.file.read(18)
    self.file_type = self.__predict_filetype()
    self.file_content = self.file.seek_at(16 * 4 + 4, self.original_file_size)
    self.decoded = (self.__get_file_decoded()).getvalue()
    return self

  def __get_file_decoded(self):
    file_bytes = io.BytesIO()
    key = self.__key(self.file_content[0], self.file_type)
    for x in range(18):
      c = bytes([self.file_content[x] ^ key])
      file_bytes.write(c)
    file_bytes.write(self.file_content[18:])
    return file_bytes

  def __key(self, x, filetype):
    if filetype == "dds":
      return int(x) ^ int('0x44', 0)
    if filetype == "jpg":
      return int(x) ^ int('0xFF', 0)
    if filetype == "bmp":
      return int(x) ^ int('0x42', 0)
    return 0

  def __predict_filetype(self):
    header_zero = 16*4+4

    check = self.file.seek_at(self.file.size-18-16*4, 18)
    if check == b"\x54\x52\x55\x45\x56\x49\x53\x49\x4F\x4E\x2D\x58\x46\x49\x4C\x45\x2E\x00":
      return "tga"

    check = self.file.seek_at(header_zero, 3)
    op = int(check[0]) ^ int('0x44', 0)
    if int(check[1]) ^ op == int('0x44', 0) and int(check[2]) ^ op == int('0x53', 0):
      return "dds"

    check_header = self.file.seek_at(header_zero, 3)
    op = int(check_header[0]) ^ int('0xFF', 0)
    check_footer = self.file.seek_at(self.file.size-2-16*4, 2)
    if int(check[1]) ^ op == int('0xD8', 0) and int(check[2]) ^ op == int('0xFF', 0) and check_footer == b"\xFF\xD9":
      return "jpg"
    
    check = self.file.seek_at(header_zero, 2)
    op = int(check_header[0]) ^ int('0x42', 0)
    if int(check[1]) ^ op == int('0x4D', 0):
      return "bmp"

    return "unknown"
