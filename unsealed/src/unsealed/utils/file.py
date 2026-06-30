# unsealed/io/binary_reader.py
import struct
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
  from ..vfs.resource import Resource

# What decoders may be handed as their source: raw bytes, a real path, or a
# vfs Resource (a duck-typed object exposing ``read() -> bytes``). Kept here
# so the formats layer never imports ``vfs`` at runtime (avoids a cycle).
FileLike = Union[bytes, Path, "Resource"]


def _read_bytes(data: "FileLike") -> bytes:
  if isinstance(data, (bytes, bytearray)):
    return bytes(data)
  if isinstance(data, Path):
    with open(data, "rb") as f:
      return f.read()
  return data.read()  # Resource / any object exposing read() -> bytes


class File:
  def __init__(self, data: "FileLike"):
    self._stream = BytesIO(_read_bytes(data))

  # Compatibility methods (same names as your File class)
  def read(self, num_bytes: int) -> bytes:
    return self._stream.read(num_bytes)

  def read_short(self) -> int:
    return struct.unpack("<H", self._stream.read(2))[0]

  def read_int(self) -> int:
    return struct.unpack("<i", self._stream.read(4))[0]

  def read_float(self) -> float:
    return struct.unpack("<f", self._stream.read(4))[0]

  def read_string(self, num_bytes: int) -> str:
    data = self._stream.read(num_bytes)
    if len(data) > 0 and data[0] == 0xCD:
      return ""

    # Split at null
    try:
      data = data[: data.index(0)]
    except ValueError:
      pass

    # Try decode
    for encoding in ["euc_kr", "windows-1252", "utf-8"]:
      try:
        return data.decode(encoding)
      except (UnicodeDecodeError, LookupError):
        continue
    return ""

  def read_string_compact(self) -> str:
    chars = []
    while True:
      byte = self._stream.read(1)
      if not byte or byte[0] == 0:
        break
      chars.append(byte)
    return b"".join(chars).decode("utf-8")

  def seek(self, num_bytes: int) -> bytes:
    pos = self._stream.tell()
    data = self._stream.read(num_bytes)
    self._stream.seek(pos)
    return data

  def seek_at(self, index_start: int, num_bytes: int) -> bytes:
    self._stream.seek(index_start)
    return self._stream.read(num_bytes)

  def is_end(self) -> bool:
    pos = self._stream.tell()
    self._stream.seek(0, 2)
    end = self._stream.tell()
    self._stream.seek(pos)
    return pos >= end

  def read_until_end(self) -> bytes:
    return self._stream.read()

  def reset(self):
    self._stream.seek(0)

  @property
  def pointer(self) -> int:
    return self._stream.tell()

  @property
  def size(self) -> int:
    pos = self._stream.tell()
    self._stream.seek(0, 2)
    size = self._stream.tell()
    self._stream.seek(pos)
    return size
