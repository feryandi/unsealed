"""SellerFile body decoder.

Layout (v1), after the shared 64-byte header + int32 count:

    int32   extra        (= 30; matches the slots/record)
    record[count]        each 120 bytes = 30 little-endian int32

Each record is a seller/shop: a zero-terminated list of up to 30 item
ids it offers (referencing ItemFile). `id` is the row index; empty
sellers (all-zero) are placeholders.
"""

import struct

from ...assets.dat import DatFile
from ...utils.file import File
from .registry import DatBody, register

_SLOTS = 30
_RECORD = _SLOTS * 4  # 120 bytes
_UNPACK = struct.Struct(f"<{_SLOTS}i")


class SellerDataBody(DatBody):
  type_name = "Seal Online SellerFile"
  versions = (1,)

  def decode(self, file: File, dat: DatFile) -> None:
    dat.unknown["header_extra"] = file.read_int()

    sellers = []
    for idx in range(dat.count):
      slots = _UNPACK.unpack(file.read(_RECORD))
      items = []
      for v in slots:  # zero-terminated list of item ids
        if v == 0:
          break
        items.append(v)
      sellers.append({"id": idx, "item_count": len(items), "items": items})
    dat.elements = sellers


register(SellerDataBody())
