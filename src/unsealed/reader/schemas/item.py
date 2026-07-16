"""ItemFile (`Seal Online ItemFile`) schemas -- three on-disk layouts.

v4 (`ITEM_V4_SCHEMA`): fixed 176-byte block with a null-terminated name
at its start (numeric fields fill the rest and are dropped) + a
null-terminated `description`. Walks exactly `count` records; `id` is the
row index (record 0 is a placeholder named "a").

v10 / v12 (`ITEM_V10_SCHEMA`, `ITEM_V12_SCHEMA`): `int32 id` +
length-prefixed `name` + stat fields (int32/float, mapped below) +
length-prefixed `description`. The two are the SAME layout -- identical
stat names at identical indices -- and differ only in how many stats
follow (82 vs 84), so they share one map and one builder.

v10/v12 are also the layout of the headerless `.ed<n>` bands: the same
records with no file header, which the band reads by resolving this
schema off its companion `item.edt` master (see `formats/edt/band.py`).
"""

from typing import Tuple

from ..formats.bytefields import (
  Column,
  Cstr,
  RecordSchema,
  F32,
  I32,
  Pstr,
  Str,
  register_schema,
)

# --- v4 -------------------------------------------------------------------

ITEM_V4_SCHEMA = RecordSchema(
  name="item_v4",
  index_field="id",
  columns=(
    Column("name", Str(176)),  # name = leading cstring; numeric tail dropped
    Column("description", Cstr),
  ),
)

register_schema(
  "dat",
  ITEM_V4_SCHEMA,
  type_names=("Seal Online ItemFile",),
  versions=(4,),
)

# --- v10 / v12 ------------------------------------------------------------

# Stat index -> name. Shared: v12 is v10 plus two more (still
# unidentified) stats at the end.
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
  31: "set_id",
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
  57: "str_refine_increment",
  58: "agi_min",
  59: "agi_refine_increment",
  60: "int_min",
  61: "int_refine_increment",
  62: "sta_min",
  63: "sta_refine_increment",
  64: "wis_min",
  65: "wis_refine_increment",
  66: "luck_min",
  67: "luck_refine_increment",
  69: "job_restriction",  # 0x1FFFFF = all jobs
  70: "model_id",
  71: "icon_id",
}
# Per-refine stat increments are float-encoded.
_STAT_FLOATS = frozenset({57, 59, 61, 63, 65, 67})


def _stat_columns(count: int) -> Tuple[Column, ...]:
  """The first `count` stat cells. An index nobody has identified yet
  falls back to `stat_<i>`, so an unknown column still reads (and keeps
  its position visible)."""
  return tuple(
    Column(_STAT_MAP.get(i, f"stat_{i}"), F32 if i in _STAT_FLOATS else I32)
    for i in range(count)
  )


def _itemfile_schema(name: str, stat_count: int) -> RecordSchema:
  """`id` + length-prefixed `name` + `stat_count` stats + `description`.

  `until_eof`: the header `count` is the GLOBAL item total across all id
  bands while the file holds only the leading band, so records are walked
  to EOF and the header count is kept as `declared_count`.
  """
  return RecordSchema(
    name=name,
    until_eof=True,
    columns=(Column("id", I32), Column("name", Pstr))
    + _stat_columns(stat_count)
    + (Column("description", Pstr),),
  )


ITEM_V10_SCHEMA = _itemfile_schema("item_v10", 82)
ITEM_V12_SCHEMA = _itemfile_schema("item_v12", 84)

register_schema(
  "dat",
  ITEM_V10_SCHEMA,
  type_names=("Seal Online ItemFile",),
  versions=(10,),
)

register_schema(
  "dat",
  ITEM_V12_SCHEMA,
  type_names=("Seal Online ItemFile",),
  versions=(12,),
)
