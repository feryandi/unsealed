# unsealed/io/binary_reader.py
import struct
from io import BytesIO
from pathlib import PurePosixPath
from typing import List


class File:
  """A binary reader over an in-memory buffer, plus the source's logical
  name.

  This is the *only* thing a decoder is handed: the bytes to decode and
  the name they came from (so a decoder can derive a stem/extension
  without ever touching a filesystem path or the archive the bytes were
  read out of). The upper layer -- a pipeline, a `BaseFormat`, or the
  viewer -- decides whether those bytes come from disk or a mounted
  `.spak` and constructs the `File`; the decoder only decodes.
  """

  def __init__(self, data: bytes, name: str = "") -> None:
    self._data = bytes(data)
    self._stream = BytesIO(self._data)
    self._name = str(name).replace("\\", "/")

  # ── source identity (mirrors the pathlib leaf API decoders relied on) ──

  @property
  def data(self) -> bytes:
    """The whole underlying buffer, independent of the read position.

    For decoders that process the entire input at once (text tables,
    stream ciphers) rather than reading it field by field."""
    return self._data

  @property
  def name(self) -> str:
    return PurePosixPath(self._name).name

  @property
  def stem(self) -> str:
    return PurePosixPath(self._name).stem

  @property
  def suffix(self) -> str:
    return PurePosixPath(self._name).suffix

  @property
  def suffixes(self) -> List[str]:
    return PurePosixPath(self._name).suffixes

  # Compatibility methods (same names as your File class)
  def read(self, num_bytes: int) -> bytes:
    return self._stream.read(num_bytes)

  def read_short(self) -> int:
    return struct.unpack("<H", self._stream.read(2))[0]

  def read_int(self) -> int:
    return struct.unpack("<i", self._stream.read(4))[0]

  def read_uint(self) -> int:
    return struct.unpack("<I", self._stream.read(4))[0]

  def read_float(self) -> float:
    return struct.unpack("<f", self._stream.read(4))[0]

  def read_ints(self, count: int) -> List[int]:
    """Read `count` consecutive little-endian int32s as a list.

    Replaces the per-decoder ``struct.Struct("<Ni")`` bulk unpacks used
    for fixed-width record grids (monster/seller/pet-food/data rows)."""
    return list(struct.unpack(f"<{count}i", self._stream.read(count * 4)))

  def read_cstring(self) -> bytes:
    """Read a null-terminated byte string (the null is consumed).

    Returns the raw bytes so the caller can pick the text encoding"""
    out = bytearray()
    while True:
      ch = self._stream.read(1)
      if not ch or ch == b"\x00":
        break
      out += ch
    return bytes(out)

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
