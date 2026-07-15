"""Headerless ItemFile band (`.ed1`, `.ed2`, … `.ed<n>`) -> `DatFile`.

An `.ed<n>` shard is an ordinary `.edt`-encrypted file (same LCG cipher,
see `codec.py`) whose plaintext is a flat list of item records with NO
64-byte header and no element count. Each shard holds one band of the
item id space (`.ed1` = 1000-1999 … `.ed17` = 17000-…).

**A band never says what it is.** With no header there is nothing to
classify, so the layout comes from its companion `<stem>.edt` — the
headered master the bands were split from, which an `.edp` bundles
alongside them (`ITEM.EDT` + `ITEM.ED1`..`ITEM.ED17`). Read the master's
title, resolve its schema, walk the band with it. That is what keeps
`.edt` and `.ed<n>` on ONE schema: when the client bumps its ItemFile
version, the bands follow their master instead of silently mis-reading
against a hardcoded layout.

Identifying the master is cheap: the `.edt` keystream chains from a fixed
seed, so a *prefix* decrypts on its own and only the first 68 bytes of a
400 KB master are touched.

Older clients ship `.ed14`-`.ed17` as fixed 326-byte id-only reserved
slots, which match no master schema, so the walk still falls back: a band
whose records don't land exactly on EOF is re-read as legacy. That has to
stay a probe rather than a filename rule — the same `.ed14` is legacy on
an old client but a full band inside a newer `item.edp`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ...assets.dat import DatFile

# Imported for its registration side effect: layouts are resolved out of
# the shared REGISTRY, never imported directly.
from ...schemas.dat import item as _item_schemas  # noqa: F401
from ...utils.file import File
from ..dat.decoder import parse_header
from ..records import REGISTRY, RecordSchema
from .codec import decode as edt_decode

# Used only when a band has no companion master to ask (a shard opened on
# its own): the layout every known band-shipping client has used.
_FALLBACK_TYPE = "Seal Online ItemFile"
_FALLBACK_VERSION = 10

_MASTER_SUFFIX = ".edt"
_HEADER_PROBE = 68  # 64-byte header + int32 count
_LEGACY_RECORD = 326  # int32 id + 322 reserved bytes
_MIN_RECORD = 8  # smallest sane record: id + one length field


@dataclass(frozen=True)
class BandLayout:
  """What a band's companion master says the band's records are."""

  type_name: str
  version: int
  schema: RecordSchema


def band_layout(res) -> Optional[BandLayout]:
  """Resolve a band's layout from its companion `<stem>.edt` master.

  None when there is no master, it isn't readable, or nothing in the
  REGISTRY claims it — the caller then falls back.
  """
  try:
    master = res.with_suffix(_MASTER_SUFFIX)
    if not master.exists():
      return None
    head = edt_decode(master.read()[:_HEADER_PROBE])
  except Exception:
    return None

  type_name, version = parse_header(head)
  if not type_name or version is None:
    return None
  # A master is self-describing, so its type+version names the schema.
  schema = REGISTRY.for_type("dat", type_name, version)
  return BandLayout(type_name, version, schema) if schema else None


def fallback_layout() -> Optional[BandLayout]:
  """The layout to try when a band has no master to ask."""
  schema = REGISTRY.for_type("dat", _FALLBACK_TYPE, _FALLBACK_VERSION)
  return BandLayout(_FALLBACK_TYPE, _FALLBACK_VERSION, schema) if schema else None


def _walk(plain: bytes, schema: RecordSchema) -> Optional[List[Dict[str, Any]]]:
  """Records read through `schema`.

  None means the layout doesn't fit: either a field read ran off the end
  (the schema's typed reads raise once the buffer is exhausted) or the
  walk didn't land exactly on EOF.
  """
  file = File(plain)
  records: List[Dict[str, Any]] = []
  while not file.is_end():
    if file.size - file.pointer < _MIN_RECORD:
      return None
    try:
      records.append(schema.read_record(file, len(records)))
    except Exception:
      return None
  return records if file.is_end() else None


def _walk_legacy(plain: bytes) -> List[Dict[str, Any]]:
  """Fixed 326-byte id-only records (the old `.ed14`-`.ed17` shards)."""
  file = File(plain)
  records: List[Dict[str, Any]] = []
  while file.size - file.pointer >= _LEGACY_RECORD:
    item_id = file.read_int()
    file.read(_LEGACY_RECORD - 4)  # skip the reserved tail
    records.append({"id": item_id})
  return records


def decode_item_band(
  plain: bytes, name: str = "", layout: Optional[BandLayout] = None
) -> DatFile:
  """Parse an already-decrypted `.ed<n>` payload into a `DatFile`.

  `layout` is what the companion master declared (see `band_layout`);
  without one the fallback layout is tried. A band that fits neither is
  read as legacy: version 0 and `unknown["layout"] = "legacy"`, since it
  matches no registered schema.
  """
  dat = DatFile()
  dat.source_name = name

  layout = layout or fallback_layout()
  records = _walk(plain, layout.schema) if layout else None
  if records is not None and layout is not None:
    dat.type_name = layout.type_name
    dat.version = layout.version
    dat.unknown["schema"] = layout.schema.name
  else:
    dat.type_name = _FALLBACK_TYPE
    dat.version = 0
    dat.unknown["layout"] = "legacy"
    records = _walk_legacy(plain)

  dat.elements = records
  dat.count = len(records)
  return dat
