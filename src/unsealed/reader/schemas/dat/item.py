"""ItemFile (`Seal Online ItemFile`) schemas -- two on-disk layouts.

v4 (`ITEM_V4_SCHEMA`): fixed 176-byte block with a null-terminated name
at its start (numeric fields fill the rest and are dropped) + a
null-terminated `description`. Walks exactly `count` records; `id` is the
row index (record 0 is a placeholder named "a").

v10 (`ITEM_V10_SCHEMA`): `int32 id` + length-prefixed `name` + 82 stat
fields (int32/float, mapped below) + length-prefixed `description`. The
header `count` is the GLOBAL item total across all id bands, while this
file only holds the leading band, so records are walked to EOF
(`until_eof=True`) and the header count is kept as `declared_count`.
"""

from .base import Column, Cstr, RecordSchema, F32, I32, Pstr, Str, register_schema

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

# --- v10 ------------------------------------------------------------------

_V10_STAT_MAP = {
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
_V10_FLOATS = frozenset({57, 59, 61, 63, 65, 67})

_V10_STATS = tuple(
  Column(_V10_STAT_MAP.get(i, f"stat_{i}"), F32 if i in _V10_FLOATS else I32)
  for i in range(82)
)

ITEM_V10_SCHEMA = RecordSchema(
  name="item_v10",
  until_eof=True,  # header count is a GLOBAL total; walk the leading band to EOF
  columns=(Column("id", I32), Column("name", Pstr)) + _V10_STATS + (Column("description", Pstr),),
)

register_schema(
  "dat",
  ITEM_V10_SCHEMA,
  type_names=("Seal Online ItemFile",),
  versions=(10,),
)
