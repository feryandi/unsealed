"""Seal Online `.edp` (EDT Package) container decoder.

`.edp` (e.g. `item.edp`) bundles every item-db shard into ONE file: it is
an archive whose members are ordinary `.edt`-encrypted files
(`ITEM.ED1` .. `ITEM.ED17`, `ITEM.EDT`). Two LCG cipher layers are
involved, but only the OUTER one belongs to the container:

  1. Header pass (this module) -- decrypt everything after the 16-byte
     file header with per-file parameters stored (XOR-masked) in it:
         mult = u32@4  ^ 0xC8A397EF
         add  = u32@8  ^ 0xB209DDC5
         seed = u32@12 ^ 0xF82B796A
  2. The member's own `.edt` decryption -- NOT done here. Its constants
     (seed 0x11CFD, mult 0xCE6D, add 0x58BF) are exactly `edt/codec.py`'s,
     because after pass 1 a member IS an `.edt` file, byte for byte.

So this decoder stops at pass 1: it hands out the members still
encrypted, and whoever opens one runs it through the normal `.edt` path
(`SealEdtFormat`, which claims `.edt` and `.ed<n>` alike). That keeps one
cipher implementation and lets a single member be opened on its own,
like any other archive member.

After the header pass the body is a directory of `count` (int32 @0x28)
64-byte entries starting at offset 0x50:

     +0x00  int32   member index
     +0x04  char[]  member name ("ITEM.ED1" .. "ITEM.ED13", "ITEM.EDT")
     +0x2C  int32   data offset (relative to the end of the directory)
     +0x34  int32   data size

The member payloads follow the directory contiguously.

Reverse-engineered from `EDPUnpaker.exe` (sub_402790 header pass,
sub_4026F0 block pass, sub_402800 driver).
"""

# `struct.unpack_from` is used for the container directory: its 64-byte
# entries are addressed at absolute offsets and the payload is decrypted
# in place in a mutable bytearray, which the forward-only `File` stream
# (utils.file) can't model.
import struct
from pathlib import PurePosixPath

from ...assets.blob import Blob
from ...assets.directory import Directory
from ...utils.file import File

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


def _lcg_decrypt(
  buf: bytearray, start: int, length: int, seed: int, mult: int, add: int
) -> None:
  """In-place LCG stream decrypt (the shared `.edt` generator)."""
  for i in range(start, start + length):
    cipher = buf[i]
    buf[i] = cipher ^ ((seed >> 8) & 0xFF)
    fb = cipher - 256 if cipher >= 128 else cipher  # signed int8 feedback
    seed = ((seed + fb) * mult + add) & 0xFFFFFFFF


def _blob(name: str, payload: bytes) -> Blob:
  """One member as a `Blob`, split into stem + extension so the archive
  browser and the extract pipeline can rebuild "ITEM.ED1"."""
  blob = Blob()
  blob.value = payload
  path = PurePosixPath(name)
  blob.name = path.stem
  blob.extension = path.suffix.lstrip(".") or None
  return blob


class EdpDecoder:
  def __init__(self, file: File) -> None:
    self.file: File = file
    self.raw: bytes = file.data

  def decode(self) -> Directory:
    buf = bytearray(self.raw)
    directory = Directory(self.file.name)
    if len(buf) < _DIR + 4:
      return directory

    # Pass 1: header cipher over the whole body (everything past the header).
    mult = struct.unpack_from("<I", buf, 4)[0] ^ _MULT_MASK
    add = struct.unpack_from("<I", buf, 8)[0] ^ _ADD_MASK
    seed = struct.unpack_from("<I", buf, 12)[0] ^ _SEED_MASK
    _lcg_decrypt(buf, _HEADER, len(buf) - _HEADER, seed, mult, add)

    count = struct.unpack_from("<i", buf, _COUNT_OFF)[0]
    if count <= 0:
      return directory
    data = _DIR + count * _ENTRY

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
      # Still `.edt`-encrypted: the member decrypts itself when opened.
      directory.list.append(_blob(name, bytes(buf[start : start + size])))

    return directory
