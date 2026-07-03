"""Seal Online `.edp` item-package container (`item_pak.edp`).

A two-layer LCG-ciphered bundle of every item-db shard. See `decoder.py`
for the cipher passes and directory layout.
"""

from .decoder import EdpDecoder
from .format import SealEdpFormat

__all__ = ["EdpDecoder", "SealEdpFormat"]
