"""SpakArchive -- a mounted Seal Online ``.spak`` archive.

.spak files are ordinary minizip (Gilles Vollant) zips encrypted with
traditional PKWARE ZipCrypto. ``zipfile`` parses the archive and ``zlib``
inflates, so the only Seal-specific code here is computing the password.
The fully managed ``ZipFile.read`` can't be used: minizip writes a zero
encryption-header check byte, so CPython's password verification always
raises "Bad password" even with the right key. We therefore decrypt the
raw entry bytes ourselves with the ZipCrypto cipher in ``utils.zipcrypto``
(verified byte-for-byte identical to the standard library's) instead of
reaching into zipfile's private internals.

The password is not fixed: the client (AutoUpdatePlus.exe) generates it at
runtime from a small integer "format version" V, so every build appears to
use a different key. The recipe (reverse engineered from the unpacked
AutoUpdatePlus.exe):

    n        = 99999999 - V
    buf      = ("Pass" + str(n)) zero-padded to 260 bytes
    crc      = crc32(buf)
    password = SPAK_TEMPLATES[V % 4] % crc    (note: one template is %X)

V is not guessed: the client stores it in the zip's global comment as
"Seal Online Zip v<V>" and reads it back with sscanf. We read the same
comment, so the password is obtained deterministically.

Some private servers repack the archives with a **fixed** password and
an empty comment (no version to derive from). Those keys can't be
computed. They are not hardcoded here: fallback keys come from the
local key store (``spak_keystore``, populated by the recovery tool),
and if none work the reader attempts a safe, scan-only auto-recovery
from an existing client dump (``utils.spak_recover``). The right key --
derived, stored, or recovered -- is picked by trial: each candidate is
verified by decrypting the smallest entry and checking its CRC, so
official and private archives both load with no key in source.
"""

import re
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Callable, List, Optional

from ..utils.zipcrypto import ZipDecryptor


class SpakPasswordError(Exception):
  """An archive is encrypted but no known/derivable key decrypts it.

  Carries the install dir (archive's grandparent) so callers can offer
  key recovery for that private server.
  """

  def __init__(self, message: str, archive_path: Path) -> None:
    super().__init__(message)
    self.archive_path = archive_path
    self.install_dir = Path(archive_path).resolve().parent.parent


class SpakArchive:
  """A mounted .spak archive: list once, decrypt entries on demand.

  Mirrors how the game client treats an archive -- the central directory
  (file list) is read up front without decrypting anything, and a single
  entry is decrypted + inflated only when its bytes are actually read.
  Use as a context manager, or call :meth:`close` when done.
  """

  # Per-version password format strings (one uses %X, the rest %x).
  SPAK_TEMPLATES = ("#!#0%x&&!!", "^^&!@%X&&*", "#$#$&*%x!!@", "!@####%x*@#@")

  _COMMENT_VERSION = re.compile(rb"Seal Online Zip v(\d+)")
  _LOCAL_HEADER = struct.Struct("<IHHHHHIIIHH")

  @staticmethod
  def _normalize(name: str) -> str:
    return name.replace("\\", "/")

  @staticmethod
  def spak_password(version: int) -> bytes:
    """Reproduce the client's per-version archive password.

    ``zlib.crc32`` is the standard CRC-32 -- the same function the client
    calls from ``zlib1.dll`` -- so it reproduces the password exactly.
    """
    buf = (b"Pass" + str(99999999 - version).encode()).ljust(260, b"\x00")
    crc = zlib.crc32(buf) & 0xFFFFFFFF
    return (SpakArchive.SPAK_TEMPLATES[version % 4] % crc).encode()

  @staticmethod
  def comment_password(comment: bytes) -> Optional[bytes]:
    """The version-derived key from the zip comment, or ``None``.

    Returns ``None`` when the comment has no ``Seal Online Zip v<N>``
    version (e.g. private repacks with an empty comment).
    """
    m = SpakArchive._COMMENT_VERSION.search(comment or b"")
    return SpakArchive.spak_password(int(m.group(1))) if m else None

  def __init__(
    self, path: Path, on_status: Optional[Callable[[str], None]] = None
  ) -> None:
    self.path = path
    # Progress callback for the (potentially slow) key resolution, so a
    # UI can say what it's doing instead of appearing to hang.
    self._on_status: Callable[[str], None] = on_status or (lambda _m: None)
    self._zf = zipfile.ZipFile(path, "r")
    self._fp = open(path, "rb")
    self.infos: List[zipfile.ZipInfo] = [
      i for i in self._zf.infolist() if not i.is_dir()
    ]
    self._by_name = {self._normalize(i.filename): i for i in self.infos}
    self.password = self._resolve_key()

  def _resolve_key(self) -> Optional[bytes]:
    """Pick the archive password, verifying candidates by trial.

    ``None`` for plain (unencrypted) archives. Tries the comment-derived
    key, then the stored fallback keys, then (unless disabled) a
    scan-only auto-recovery from an existing client dump -- taking the
    one that decrypts the smallest entry to its CRC. Raises if none do.
    """
    if not any(i.flag_bits & 0x1 for i in self.infos):
      return None

    from . import spak_keystore

    sample = min(self.infos, key=lambda i: i.compress_size)
    candidates: List[bytes] = []
    derived = self.comment_password(self._zf.comment)
    if derived is not None:
      candidates.append(derived)
    candidates.extend(spak_keystore.load_keys())

    for pw in candidates:
      if self._password_ok(pw, sample):
        return pw

    recovered = self._auto_recover(sample)
    if recovered is not None:
      return recovered

    raise SpakPasswordError(
      f"{Path(self.path).name!r} is encrypted but no known key decrypts it "
      f"(comment={self._zf.comment[:40]!r}). Recover the private-server key "
      f"with 'unsealed-reader recover-key', then it will load automatically.",
      Path(self.path),
    )

  def _auto_recover(self, sample: zipfile.ZipInfo) -> Optional[bytes]:
    """Scan an existing client memory dump near the install for the key.

    Safe and non-interactive: only reads existing dumps, never launches
    a process. CRC-gated by this archive, so an unrelated dump yields
    nothing. A hit is saved to the key store so it loads without a scan
    next time. Disable with ``UNSEALED_SPAK_NO_AUTORECOVER=1``.
    """
    import os

    if os.environ.get("UNSEALED_SPAK_NO_AUTORECOVER"):
      return None
    install = Path(self.path).resolve().parent.parent
    try:
      from . import spak_keystore
      from ..utils import spak_recover
    except Exception:
      return None

    def verify(pw: bytes) -> bool:
      return self._password_ok(pw, sample)

    found = spak_recover.recover_from_existing_dumps(
      verify, install, on_status=self._on_status
    )
    if found is None:
      return None
    key, _dump = found
    spak_keystore.save_key(key, label=install.name)
    return key

  def _read_stored(self, info: zipfile.ZipInfo) -> bytes:
    """Raw stored bytes of an entry (still encrypted/compressed)."""
    lh = self._LOCAL_HEADER
    self._fp.seek(info.header_offset)
    header = lh.unpack(self._fp.read(lh.size))
    # The local header's name/extra lengths give the true data offset
    # (they may differ from the central directory's extra length).
    self._fp.seek(info.header_offset + lh.size + header[9] + header[10])
    return self._fp.read(info.compress_size)

  def _password_ok(self, password: bytes, info: zipfile.ZipInfo) -> bool:
    """True if ``password`` decrypts ``info`` to its recorded CRC."""
    try:
      out = self._inflate(self._read_stored(info), info, password)
    except Exception:
      return False
    return (zlib.crc32(out) & 0xFFFFFFFF) == info.CRC

  @staticmethod
  def _inflate(raw: bytes, info: zipfile.ZipInfo, password: Optional[bytes]) -> bytes:
    """Decrypt (if keyed) and decompress raw stored bytes."""
    if info.flag_bits & 0x1:  # encrypted -> 12-byte header precedes the data
      if password is None:
        raise Exception(f"{info.filename!r} is encrypted but no key was found")
      raw = ZipDecryptor(password).decrypt(raw)[12:]
    if info.compress_type == zipfile.ZIP_DEFLATED:
      return zlib.decompress(raw, -15)
    if info.compress_type == zipfile.ZIP_STORED:
      return raw
    raise Exception(
      f"Unsupported compression {info.compress_type} for {info.filename!r}"
    )

  def __enter__(self) -> "SpakArchive":
    return self

  def __exit__(self, *exc) -> None:
    self.close()

  def names(self) -> List[str]:
    """All file entry names (normalized to forward slashes)."""
    return list(self._by_name.keys())

  def info(self, name: str) -> Optional[zipfile.ZipInfo]:
    return self._by_name.get(self._normalize(name))

  def read(self, entry) -> bytes:
    """Decrypt + inflate a single entry (a name or ZipInfo)."""
    info = entry if isinstance(entry, zipfile.ZipInfo) else self.info(entry)
    if info is None:
      raise KeyError(f"{entry!r} not found in {self.path.name!r}")
    return self._inflate(self._read_stored(info), info, self.password)

  def close(self) -> None:
    self._fp.close()
    self._zf.close()
