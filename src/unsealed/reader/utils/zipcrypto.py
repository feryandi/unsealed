"""Traditional PKWARE ZipCrypto stream cipher (APPNOTE.TXT 6.1.5).

A standalone reimplementation of the cipher the standard library runs
internally, so callers depend only on ``zipfile``'s public API rather
than its private ``_ZipDecrypter``. Used to decrypt Seal Online ``.spak``
entries, whose minizip-written check byte makes the fully managed
``ZipFile.read`` reject them (see ``assets/spak.py``).
"""


class ZipDecryptor:
  """A ZipCrypto keystream keyed by the archive password.

  Decrypts entry bytes one at a time via three rolling 32-bit keys, byte
  for byte identical to the standard library's cipher. The leading
  12-byte encryption header is decrypted along with the data and dropped
  by the caller.
  """

  @staticmethod
  def _make_crc32_table() -> tuple:
    """The reflected CRC-32 table (polynomial 0xEDB88320) ZipCrypto uses."""
    table = []
    for i in range(256):
      c = i
      for _ in range(8):
        c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
      table.append(c)
    return tuple(table)

  _CRC32_TABLE = _make_crc32_table()

  def __init__(self, password: bytes) -> None:
    self._k0, self._k1, self._k2 = 0x12345678, 0x23456789, 0x34567890
    for byte in password:
      self._update(byte)

  @classmethod
  def from_keys(cls, k0: int, k1: int, k2: int) -> "ZipDecryptor":
    """Build a decryptor from the three internal keys directly.

    The password derives these three 32-bit keys once (see
    ``__init__``); a known-plaintext attack (bkcrack) recovers the same
    keys without the password, which private servers make too long to
    brute-force. Decryption only reads the keys, so this suffices --
    the recovered keys, like the password, decrypt every entry.
    """
    self = cls.__new__(cls)
    self._k0 = k0 & 0xFFFFFFFF
    self._k1 = k1 & 0xFFFFFFFF
    self._k2 = k2 & 0xFFFFFFFF
    return self

  def _update(self, ch: int) -> None:
    self._k0 = (self._k0 >> 8) ^ self._CRC32_TABLE[(self._k0 ^ ch) & 0xFF]
    self._k1 = (self._k1 + (self._k0 & 0xFF)) & 0xFFFFFFFF
    self._k1 = (self._k1 * 134775813 + 1) & 0xFFFFFFFF
    self._k2 = (self._k2 >> 8) ^ self._CRC32_TABLE[(self._k2 ^ (self._k1 >> 24)) & 0xFF]

  def decrypt(self, data: bytes) -> bytes:
    out = bytearray(len(data))
    for i, c in enumerate(data):
      k = self._k2 | 2
      c ^= ((k * (k ^ 1)) >> 8) & 0xFF
      self._update(c)
      out[i] = c
    return bytes(out)
