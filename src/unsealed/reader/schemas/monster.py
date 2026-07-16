"""MonsterDataFile (`SealOnline MonsterDataFile v12`) as a schema.

After the shared header + count there is ONE extra int32 (`header_extra`),
then `count` records of 64 int32 fields. `field[0]` is the monster id
(contiguous 1..count); other fields are numeric stats, named below where
known (the rest stay `field_N`). Model id (`model_id`, field 38) indexes
the Mon_Grapic table; `talk_id` (42) joins the QuestFile dialog tree.
"""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

_NAMED = {
  0: "id",
  4: "level",
  6: "hp",
  8: "movement_speed",
  10: "attack_range",
  12: "element",
  14: "critical_hit",
  16: "critical_hit_defense",
  18: "hit_rate",
  20: "evasion_rate",
  22: "attack",
  24: "defense",
  26: "exp",
  28: "loot_id",
  # 3 = non-attackable interactive entity (NPCs, gacha, warp, statues…);
  # attackable monsters use other values (0/1/2/6…).
  32: "category",
  38: "model_id",
  42: "talk_id",
  44: "seller_id",
  52: "respawn_time",
  56: "aggro_range",
}

MONSTER_SCHEMA = RecordSchema(
  name="monster_data",
  header_extra=1,
  columns=tuple(Column(_NAMED.get(i, f"field_{i}"), I32) for i in range(64)),
)

register_schema(
  "dat",
  MONSTER_SCHEMA,
  type_names=("SealOnline MonsterDataFile",),
  versions=(12,),
)
