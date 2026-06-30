import re
import struct
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import List, Optional

from ...assets.blob import Blob
from ...assets.directory import Directory

# --- Seal Online .spak password scheme --------------------------------
#
# .spak files are ordinary minizip (Gilles Vollant) zips encrypted with
# traditional PKWARE ZipCrypto. We let the standard library do the heavy
# lifting -- ``zipfile`` parses the archive and runs the stream cipher,
# ``zlib`` inflates -- so the only Seal-specific code here is computing
# the password. (We can't use the fully managed ``ZipFile.read`` because
# minizip writes a zero encryption-header check byte, which CPython
# rejects; we reuse its cipher on the raw entry bytes instead.)
#
# The password is not fixed: the client (AutoUpdatePlus.exe) generates
# it at runtime from a small integer "format version" V, so every build
# appears to use a different key. The recipe (reverse engineered from
# the unpacked AutoUpdatePlus.exe):
#
#   n        = 99999999 - V
#   buf      = ("Pass" + str(n)) zero-padded to 260 bytes
#   crc      = crc32(buf)
#   password = SPAK_TEMPLATES[V % 4] % crc    (note: one template is %X)
#
# V is not guessed: the client stores it in the zip's global comment as
# "Seal Online Zip v<V>" and reads it back with sscanf. We read the same
# comment, so the password is obtained deterministically.
SPAK_TEMPLATES = ("#!#0%x&&!!", "^^&!@%X&&*", "#$#$&*%x!!@", "!@####%x*@#@")

_COMMENT_VERSION = re.compile(rb"Seal Online Zip v(\d+)")
_LOCAL_HEADER = struct.Struct("<IHHHHHIIIHH")


def spak_password(version: int) -> bytes:
  """Reproduce the client's per-version archive password.

  ``zlib.crc32`` is the standard CRC-32 -- the same function the client
  calls from ``zlib1.dll`` -- so it reproduces the password exactly.
  """
  buf = (b"Pass" + str(99999999 - version).encode()).ljust(260, b"\x00")
  crc = zlib.crc32(buf) & 0xFFFFFFFF
  return (SPAK_TEMPLATES[version % 4] % crc).encode()


def resolve_password(
  infos: List[zipfile.ZipInfo], comment: bytes, archive_name: str = "archive"
) -> Optional[bytes]:
  """Derive the password from the version in the zip comment.

  Returns ``None`` for plain (unencrypted) archives. Raises when an
  entry is encrypted but the version can't be read from the comment.
  """
  if not any(i.flag_bits & 0x1 for i in infos):
    return None

  m = _COMMENT_VERSION.search(comment or b"")
  if m is None:
    raise Exception(
      f"{archive_name!r} is encrypted but has no 'Seal Online Zip "
      f"v<N>' comment to derive the key from; pass password= explicitly."
    )
  return spak_password(int(m.group(1)))


def _normalize(name: str) -> str:
  return name.replace("\\", "/")


class SpakArchive:
  """A mounted .spak archive: list once, decrypt entries on demand.

  Mirrors how the game client treats an archive -- the central directory
  (file list) is read up front without decrypting anything, and a single
  entry is decrypted + inflated only when its bytes are actually read.
  Use as a context manager, or call :meth:`close` when done.
  """

  def __init__(self, path: Path, password: Optional[bytes] = None) -> None:
    self.path = path
    self._zf = zipfile.ZipFile(path, "r")
    self._fp = open(path, "rb")
    self.infos: List[zipfile.ZipInfo] = [
      i for i in self._zf.infolist() if not i.is_dir()
    ]
    self.password = password or resolve_password(
      self.infos, self._zf.comment, path.name
    )
    self._by_name = {_normalize(i.filename): i for i in self.infos}

  def __enter__(self) -> "SpakArchive":
    return self

  def __exit__(self, *exc) -> None:
    self.close()

  def names(self) -> List[str]:
    """All file entry names (normalized to forward slashes)."""
    return list(self._by_name.keys())

  def info(self, name: str) -> Optional[zipfile.ZipInfo]:
    return self._by_name.get(_normalize(name))

  def read(self, entry) -> bytes:
    """Decrypt + inflate a single entry (a name or ZipInfo)."""
    info = entry if isinstance(entry, zipfile.ZipInfo) else self.info(entry)
    if info is None:
      raise KeyError(f"{entry!r} not found in {self.path.name!r}")

    self._fp.seek(info.header_offset)
    header = _LOCAL_HEADER.unpack(self._fp.read(_LOCAL_HEADER.size))
    # The local header's name/extra lengths give the true data offset
    # (they may differ from the central directory's extra length).
    self._fp.seek(info.header_offset + _LOCAL_HEADER.size + header[9] + header[10])
    raw = self._fp.read(info.compress_size)

    if info.flag_bits & 0x1:  # encrypted -> 12-byte header precedes the data
      if self.password is None:
        raise Exception(f"{info.filename!r} is encrypted but no key was found")
      raw = zipfile._ZipDecrypter(self.password)(raw)[12:]

    if info.compress_type == zipfile.ZIP_DEFLATED:
      return zlib.decompress(raw, -15)
    if info.compress_type == zipfile.ZIP_STORED:
      return raw
    raise Exception(
      f"Unsupported compression {info.compress_type} for {info.filename!r}"
    )

  def close(self) -> None:
    self._fp.close()
    self._zf.close()


class SpakDecoder:
  """Decodes a Seal Online .spak archive into a Directory of Blobs.

  Reads every entry. The password is derived deterministically from the
  format version in the zip's global comment ("Seal Online Zip v<V>").
  Pass ``password`` to override it for non-standard archives.
  """

  def __init__(self, path: Path, password: Optional[bytes] = None) -> None:
    self.path: Path = path
    self.password: Optional[bytes] = password

  def decode(self) -> Directory:
    with SpakArchive(self.path, self.password) as archive:
      directory = Directory(name=self.path.stem)
      for info in archive.infos:
        directory.list.append(self._to_blob(info.filename, archive.read(info)))
    return directory

  @staticmethod
  def _to_blob(filename: str, content: bytes) -> Blob:
    name = _normalize(filename)
    pure = PurePosixPath(name)
    blob = Blob()
    blob.value = content
    blob.extension = pure.suffix.lstrip(".") or None
    # Keep any sub-directory prefix so the layout can be reproduced.
    blob.name = name[: -len(pure.suffix)] if pure.suffix else name
    return blob
