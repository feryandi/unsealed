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

# --- item.scr (plain-text pipe-delimited script) option-scale columns -----
#
# NOT the same coordinate system as `_STAT_MAP` above. `_STAT_MAP` indexes
# stat *cells* inside the compiled binary `.dat`/`.edt` ItemFile record
# (`byte_offset = 4 * stat_index`, after the `id`+`name` header). `item.scr`
# is a completely separate, plain-text server script -- one pipe-delimited
# line per item (`line_number == item_id + 1`; field 0 repeats the item id
# as a sanity check) -- with its own field layout that has to be derived
# independently; there is currently no schema/registry wiring for `.scr`
# files in this codebase (they decode as a raw `CellTable`, see
# `formats/scr/format.py` / `assets/scr.py`), so this map is reference-only
# for now, not consumed by a decoder.
#
# These are the per-item "Magic/Spring Option Appraiser" scale columns for
# `GC_ITEM_CONFIRM_NPC_SUCC` (see the sibling `OpenShiltz` repo's
# `game/handlers/gc_item_confirm_npc_succ.py`): that packet's `option_bits`
# packs 10 gates x 3-bit tiers (baseline tier 2), and the displayed bonus
# is `(tier - 2) * item.scr[item_id][field]` -- i.e. the "scale" is a
# per-item, per-gate value read straight out of item.scr, NOT a fixed
# constant (an earlier pass wrongly assumed a universal per-gate constant
# because each gate had only ever been tested against a single item;
# confirmed wrong 2026-08-06 once one item -- id 7938 -- was tested against
# every gate at once and showed scale=1 uniformly instead of the
# previously-"confirmed" x5/x2/x3 values).
#
# Found by brute-forcing all 86 pipe-delimited fields of items
# 150/4527/4530/5953/7938/99/16682 against known (item, gate, real
# displayed scale) pairs from real packet captures. All 10 gates are now
# CONFIRMED against at least two independent real items each.
# gate index (as packed in GC_ITEM_CONFIRM_NPC_SUCC's option_bits) ->
# (name, item.scr pipe-field index).
ITEM_SCR_OPTION_SCALE_FIELD = {
  0: ("damage", 10),          # CONFIRMED: item 150 field=5, item 7938 field=1
  1: ("magic_power", 16),     # CONFIRMED: item 5953 field=5, item 7938 field=1
  2: ("defense", 21),         # CONFIRMED: item 7938 field=1 (only sample so far)
  3: ("attack_speed", 24),    # CONFIRMED: item 99 field=3, item 16682 field=2
  4: ("accuracy", 26),        # CONFIRMED: item 99 field=2, item 16682 field=2
  5: ("critical_rate", 28),   # CONFIRMED: item 99 field=2, item 16682 field=2
  6: ("evasion_rate", 30),    # CONFIRMED: item 4527 field=1, item 7938 field=1
  7: ("movement_speed", 32),  # CONFIRMED: item 4530 field=3, item 7938 field=1
                               # -- the ONLY field of all 86 that fits both
  8: ("hp_percent", 38),      # CONFIRMED: item 99 field=2, item 16682 field=2
  9: ("ap_percent", 40),      # CONFIRMED: item 5953 field=1, item 7938 field=1
}


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
