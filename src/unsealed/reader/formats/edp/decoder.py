"""Seal Online `.edp` item-package container decoder.

`.edp` (e.g. `item_pak.edp`) bundles every item-db shard into ONE file
behind a two-layer LCG stream cipher. Both layers are the same generator
as `.edt` (keystream byte = high byte of the running seed; the seed
chains on the ciphertext byte) and differ only in seed/multiplier/addend:

  1. Header pass -- decrypt the whole body after the 16-byte file header
     with per-file parameters stored (XOR-masked) in that header:
         mult = u32@4  ^ 0xC8A397EF
         add  = u32@8  ^ 0xB209DDC5
         seed = u32@12 ^ 0xF82B796A
  2. Block pass -- decrypt each member's bytes again with the fixed `.edt`
     constants (seed 0x11CFD, mult 0xCE6D, add 0x58BF).

After the header pass the body is a directory of `count` (int32 @0x28)
64-byte entries starting at offset 0x50:

     +0x00  int32   member index
     +0x04  char[]  member name ("ITEM.ED1" .. "ITEM.ED13", "ITEM.EDT")
     +0x2C  int32   data offset (relative to the end of the directory)
     +0x34  int32   data size

The member payloads follow the directory contiguously. `ITEM.ED<n>`
members are flat item-db record lists (parsed by `formats.ed`); the lone
`ITEM.EDT` member is a "Seal Online ItemFile v10" `.dat` (parsed by the
`.dat` framework). The keystream byte only depends on the seed mod 2**16,
so full 32-bit state and 0xFFFF-masked state are equivalent.

Reverse-engineered from `EDPUnpaker.exe` (sub_402790 header pass,
sub_4026F0 block pass, sub_402800 driver).
"""

# `struct.unpack_from` is used for the container directory: its 64-byte
# entries are addressed at absolute offsets and the payload is decrypted
# in place in a mutable bytearray, which the forward-only `File` stream
# (utils.file) can't model. Members, once sliced out, ARE parsed through
# the File-based `.dat` / item-db decoders.
import struct

from ...assets.edp import EdpArchive
from ...utils.file import File
from ..dat.decoder import SealDatDecoder
from ..ed.decoder import parse_item_db

_HEADER = 0x10
_DIR = 0x50
_ENTRY = 64
_COUNT_OFF = 0x28
_NAME_MAX = 40
_OFF_FIELD = 0x2C
_SIZE_FIELD = 0x34

# XOR masks for the per-file header-cipher parameters (from EDPUnpaker).
_MULT_MASK = 0xC8A397EF
_ADD_MASK = 0xB209DDC5
_SEED_MASK = 0xF82B796A

# Fixed `.edt` cipher constants for the per-member block pass.
_ED_SEED, _ED_MULT, _ED_ADD = 0x11CFD, 0xCE6D, 0x58BF


def _lcg_decrypt(
  buf: bytearray, start: int, length: int, seed: int, mult: int, add: int
) -> None:
  """In-place LCG stream decrypt (the shared `.edt` generator)."""
  for i in range(start, start + length):
    cipher = buf[i]
    buf[i] = cipher ^ ((seed >> 8) & 0xFF)
    fb = cipher - 256 if cipher >= 128 else cipher  # signed int8 feedback
    seed = ((seed + fb) * mult + add) & 0xFFFFFFFF


class EdpDecoder:
  def __init__(self, file: File) -> None:
    self.file: File = file
    self.raw: bytes = file.data

  def decode(self) -> EdpArchive:
    buf = bytearray(self.raw)
    arc = EdpArchive()
    arc.source_name = self.file.name
    if len(buf) < _DIR + 4:
      return arc

    # Pass 1: header cipher over the whole body (everything past the header).
    mult = struct.unpack_from("<I", buf, 4)[0] ^ _MULT_MASK
    add = struct.unpack_from("<I", buf, 8)[0] ^ _ADD_MASK
    seed = struct.unpack_from("<I", buf, 12)[0] ^ _SEED_MASK
    _lcg_decrypt(buf, _HEADER, len(buf) - _HEADER, seed, mult, add)

    count = struct.unpack_from("<i", buf, _COUNT_OFF)[0]
    if count <= 0:
      return arc
    data = _DIR + count * _ENTRY

    members = []
    for i in range(count):
      entry = _DIR + i * _ENTRY
      if entry + _ENTRY > len(buf):
        break
      raw_name = bytes(buf[entry + 4 : entry + 4 + _NAME_MAX])
      name = raw_name.split(b"\x00", 1)[0].decode("latin-1", "ignore")
      offset = struct.unpack_from("<i", buf, entry + _OFF_FIELD)[0]
      size = struct.unpack_from("<i", buf, entry + _SIZE_FIELD)[0]
      start = data + offset
      if size < 0 or start < 0 or start + size > len(buf):
        continue
      # Pass 2: fixed `.edt` cipher over just this member's bytes.
      _lcg_decrypt(buf, start, size, _ED_SEED, _ED_MULT, _ED_ADD)
      members.append(self._parse_member(name, bytes(buf[start : start + size])))

    arc.members = members
    return arc

  def _parse_member(self, name: str, payload: bytes) -> dict:
    """Parse a decrypted member: `ITEM.EDT` is a "Seal Online ItemFile"
    `.dat`; the `ITEM.ED<n>` shards are flat item-db record lists."""
    if payload[:11] == b"Seal Online" or payload[:10] == b"SealOnline":
      dat = SealDatDecoder(File(payload)).decode()
      return {
        "name": name,
        "format": f"{dat.type_name} v{dat.version}",
        "count": len(dat.elements),
        "items": dat.elements,
      }
    fmt, items = parse_item_db(payload)
    return {"name": name, "format": fmt, "count": len(items), "items": items}
