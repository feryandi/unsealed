import struct
import traceback


# Lightweight file reader
class File:
  def __init__(self, content):
    self.content = content
    self.pointer = 0
    self.size = len(content)

  def is_end(self):
    return len(self.content) <= self.pointer + 1

  def seek(self, num_bytes):
    d = self.content[self.pointer : self.pointer + num_bytes]
    return d

  def read_until_end(self):
    return self.read(len(self.content) - self.pointer)

  # Reading data will move the pointer forward
  # make it impossible to read previous bytes
  def read(self, num_bytes):
    d = self.seek(num_bytes)
    self.pointer += num_bytes
    return d

  def read_short(self):
    return struct.unpack("H", self.read(2))[0]

  def read_int(self):
    return struct.unpack("I", self.read(4))[0]

  def read_float(self):
    return struct.unpack("f", self.read(4))[0]

  # TODO: Cleanup
  def read_string_compact(self):
    d = self.read(1)
    s = []
    while d[0] != 0:
      s.append(d[0])
      d = self.read(1)
    return bytearray(s).decode("utf-8")

  def read_string(self, num_bytes):
    d = self.read(num_bytes)
    if d[0] == 205:  # TODO: What is 205?
      # Null value
      return None
    try:
      s = d.split(b"\x00")[0].decode("euc_kr")
      return s
    except Exception:
      try:
        s = d.split(b"\x00")[0].decode("windows-1252")
        return s
      except Exception as e:
        print(traceback.format_exc())
        print(e)
        return None

  def seek_at(self, index_start, num_bytes):
    d = self.content[index_start : index_start + num_bytes]
    return d

  def reset(self):
    self.pointer = 0
