"""Seal Online item-database (`.ed1`, `.ed2`, … `.ed<n>`) decoder.

An `.ed<n>` shard is EDT-encrypted (the same LCG stream cipher as
`.edt` — reused from `formats/edt/codec.py`), so it is decrypted first.
The plaintext is NOT a `Seal Online ...File` header, so it never gets
claimed by the `.dat` decoders; instead it is a flat list of item
records read straight to EOF (no file header / count):

    record (modern, "item-db"):
        int32   id            item id (contiguous within the shard band)
        int32   name_len
        name    name_len      EUC-KR item name
        stats   328 bytes     82 little-endian fields (item attributes;
                              labelled via `_STAT_MAP` below)
        int32   desc_len
        desc    desc_len      EUC-KR description text

The older shards (`.ed14`-`.ed17`) use a fixed 326-byte record that only
carries an id (reserved/empty slots). When the modern walk does not land
exactly on EOF we fall back to that legacy id-only layout.

To tag a stat, add its index to `_STAT_MAP` (and to `_STAT_FLOATS` if it
is float-encoded); unmapped indices surface as `stat_<i>`. Same pattern
as SkillFile (`skill.py`) and Buff (`buff.py`).
"""

from ...assets.eddb import ItemDb
from ...utils.file import File
from ..edt.codec import decode as edt_decrypt

_STAT_BYTES = 328
_STATS = _STAT_BYTES // 4  # 82 fields
_LEGACY_RECORD = 326

# index -> stat name (unmapped indices become "stat_<i>"). Fill in as the
# columns are reverse-engineered, e.g. {0: "item_type", 1: "model_id"}.
_STAT_MAP = {
  0: "item_type",  # 7=dagger 9=mace 17=helmet 16=suit 19/20=shoes 1=potion 3=misc
  1: "min_level",
  3: "min_fame",
  4: "damage",
  10: "magic_power",
  15: "defense",
  21: "attack_speed",
  25: "critical_rate",
  27: "evasion_rate",
  30: "movement_speed",
  33: "buy_price",
  34: "sell_price",
  35: "hp_restore",
  37: "ap_restore",
  40: "cooldown",
  41: "feeding_value",
  49: "refine_g_item_id",
  50: "refine_ac_item_id",
  51: "refine_a_item_id",
  52: "refine_c_item_id",
  55: "attack_range",
  56: "str_min",
  57: "str_refine_increment",  # per-refine STR growth (float), pairs with str_min
  58: "agi_min",
  59: "agi_refine_increment",  # float, pairs with agi_min
  60: "int_min",
  61: "int_refine_increment",  # float, pairs with int_min
  62: "sta_min",  # fills the STR/AGI/INT/STA/WIS/LUCK requirement sequence
  63: "sta_refine_increment",  # float
  64: "wis_min",
  65: "wis_refine_increment",  # float
  66: "luck_min",
  67: "luck_refine_increment",  # float, pairs with luck_min
  69: "job_restriction",  # 0x1FFFFF = all jobs
  70: "model_id",
  71: "icon_id",
}

# Indices whose int32 bits are actually an IEEE-754 float (read with
# read_float instead of read_int).
_STAT_FLOATS = frozenset({57, 59, 61, 63, 65, 67})


def _kr(data: bytes) -> str:
  """Decode a EUC-KR byte run with western fallbacks."""
  for enc in ("euc_kr", "cp1252", "utf-8"):
    try:
      return data.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return data.decode("latin-1", "replace")


def _parse_modern(plain: bytes):
  """Walk variable-length records; None if it doesn't end exactly at EOF."""
  file = File(plain)
  size = file.size
  items = []
  while not file.is_end():
    if size - file.pointer < 8:
      return None
    item_id = file.read_int()
    name_len = file.read_int()
    if name_len < 0 or file.pointer + name_len + _STAT_BYTES + 4 > size:
      return None
    name = _kr(file.read(name_len))
    stats = {}
    for i in range(_STATS):
      key = _STAT_MAP.get(i, f"stat_{i}")
      stats[key] = file.read_float() if i in _STAT_FLOATS else file.read_int()
    desc_len = file.read_int()
    if desc_len < 0 or file.pointer + desc_len > size:
      return None
    desc = _kr(file.read(desc_len))
    items.append({"id": item_id, "name": name, "stats": stats, "description": desc})
  return items if file.is_end() else None


def _parse_legacy(plain: bytes):
  """Fixed 326-byte id-only records (the old `.ed14`-`.ed17` shards)."""
  file = File(plain)
  items = []
  while file.size - file.pointer >= _LEGACY_RECORD:
    item_id = file.read_int()
    file.read(_LEGACY_RECORD - 4)  # skip the rest of the fixed record
    items.append({"id": item_id})
  return items


def parse_item_db(plain: bytes):
  """Parse an already-decrypted item-db payload into `(format, items)`.

  Tries the modern variable-length record layout first and falls back to
  the legacy fixed-size id-only layout when it doesn't land exactly on
  EOF. Shared by `ItemDbDecoder` (`.ed<n>` shards) and the `.edp`
  container decoder, so the `_STAT_MAP` schema lives in one place.
  """
  items = _parse_modern(plain)
  if items is not None:
    return "item-db", items
  return "legacy", _parse_legacy(plain)


class ItemDbDecoder:
  def __init__(self, file: File) -> None:
    self.file: File = file
    self.raw: bytes = file.data

  def decode(self) -> ItemDb:
    db = ItemDb()
    db.source_name = self.file.name
    db.format, db.items = parse_item_db(edt_decrypt(self.raw))
    return db
