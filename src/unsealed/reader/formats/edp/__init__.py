"""Seal Online `.edp` EDT package (`item.edp`).

An LCG-ciphered archive whose members are ordinary `.edt`-encrypted files
(the item-db shards). It decodes to a `Directory` of still-encrypted
members; each one decrypts through the normal `.edt` path when opened.
See `decoder.py` for the container cipher and directory layout.
"""

from .decoder import EdpDecoder
from .format import SealEdpFormat

__all__ = ["EdpDecoder", "SealEdpFormat"]
