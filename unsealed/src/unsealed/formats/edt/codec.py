"""Seal Online `.edt` cipher.

Each byte is XORed with the high byte of a running 16-bit seed; the
seed is then advanced by a linear congruential generator (LCG) fed
the *ciphertext* byte added as a signed int8. Because the keystream
chains on the ciphertext, decode and encode are exact inverses.

  seed0 = 0x11CFD
  key   = (seed >> 8) & 0xFF
  out   = in ^ key
  seed  = ((seed + signed8(cipher)) * 52845 + 22719) & 0xFFFF

`cipher` is the input byte when decoding, the output byte when
encoding.
"""

_MULT = 52845  # 0xCE6D
_ADD = 22719  # 0x58BF
_MASK = 0xFFFF
_SEED0 = 0x11CFD


def _signed8(byte: int) -> int:
  """Interpret a byte as a signed int8 (done before chaining)."""
  return byte if byte < 0x80 else byte - 0x100


def decode(data: bytes, seed: int = _SEED0) -> bytes:
  """Decrypt obfuscated `.edt` bytes into plaintext."""
  out = bytearray(len(data))
  for i, cipher in enumerate(data):
    out[i] = cipher ^ ((seed >> 8) & 0xFF)
    seed = ((seed + _signed8(cipher)) * _MULT + _ADD) & _MASK
  return bytes(out)


def encode(data: bytes, seed: int = _SEED0) -> bytes:
  """Encrypt plaintext bytes back into the obfuscated `.edt` form."""
  out = bytearray(len(data))
  for i, plain in enumerate(data):
    cipher = plain ^ ((seed >> 8) & 0xFF)
    out[i] = cipher
    seed = ((seed + _signed8(cipher)) * _MULT + _ADD) & _MASK
  return bytes(out)
