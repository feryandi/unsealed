import re
import struct
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Optional

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


class SpakDecoder:
  """Decodes a Seal Online .spak archive (a ZipCrypto-encrypted zip).

  The password is derived deterministically from the format version read
  from the zip's global comment ("Seal Online Zip v<V>"). Pass
  ``password`` to override it for archives with a non-standard comment.
  """

  def __init__(self, path: Path, password: Optional[bytes] = None) -> None:
    self.path: Path = path
    self.password: Optional[bytes] = password

  def decode(self) -> Directory:
    with zipfile.ZipFile(self.path, "r") as zf, open(self.path, "rb") as fp:
      infos = [i for i in zf.infolist() if not i.is_dir()]
      password = self.password or self._resolve_password(infos, zf.comment)

      directory = Directory(name=self.path.stem)
      for info in infos:
        directory.list.append(self._extract(fp, info, password))
    return directory

  def _resolve_password(
    self, infos: list[zipfile.ZipInfo], comment: bytes
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
        f"{self.path.name!r} is encrypted but has no 'Seal Online Zip "
        f"v<N>' comment to derive the key from; pass password= explicitly."
      )
    return spak_password(int(m.group(1)))

  def _extract(self, fp, info: zipfile.ZipInfo, password: Optional[bytes]) -> Blob:
    fp.seek(info.header_offset)
    header = _LOCAL_HEADER.unpack(fp.read(_LOCAL_HEADER.size))
    # The local header's name/extra lengths give the true data offset
    # (they may differ from the central directory's extra length).
    fp.seek(info.header_offset + _LOCAL_HEADER.size + header[9] + header[10])
    raw = fp.read(info.compress_size)

    if info.flag_bits & 0x1:  # encrypted -> 12-byte header precedes the data
      if password is None:
        raise Exception(f"{info.filename!r} is encrypted but no key was found")
      raw = zipfile._ZipDecrypter(password)(raw)[12:]

    if info.compress_type == zipfile.ZIP_DEFLATED:
      content = zlib.decompress(raw, -15)
    elif info.compress_type == zipfile.ZIP_STORED:
      content = raw
    else:
      raise Exception(
        f"Unsupported compression {info.compress_type} for {info.filename!r}"
      )

    name = info.filename.replace("\\", "/")
    pure = PurePosixPath(name)
    blob = Blob()
    blob.value = content
    blob.extension = pure.suffix.lstrip(".") or None
    # Keep any sub-directory prefix so the layout can be reproduced.
    blob.name = name[: -len(pure.suffix)] if pure.suffix else name
    return blob
