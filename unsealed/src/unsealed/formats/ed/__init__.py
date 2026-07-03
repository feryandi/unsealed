"""Seal Online item-database shards (`.ed1`, `.ed2`, … `.ed<n>`).

EDT-encrypted files whose plaintext is a flat item-record list rather
than a `Seal Online ...File` `.dat`. See `decoder.py` for the layout.
"""

from .decoder import ItemDbDecoder
from .format import SealItemDbFormat

__all__ = ["ItemDbDecoder", "SealItemDbFormat"]
