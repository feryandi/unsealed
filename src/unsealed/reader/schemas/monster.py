"""MonsterDataFile (`SealOnline MonsterDataFile v12`) as a schema."""

from ..formats.bytefields import Column, RecordSchema, I32, I64, register_schema

# `element`: 1-based element index (1 Fire, 2 Water, 3 Tree, 4 Steel,
# 5 Earth, 6 Sun, 7 Darkness, 8 Magical, 9 Physical; 0 = none).
# `category`: 3 = non-attackable interactive entity (NPCs, gacha, warp,
# statues...); attackable monsters use other values (0/1/2/6...).
_NAMED = {
  0: "id",
  2: "level",
  3: "hp",
  4: "movement_speed",
  5: "attack_range",
  6: "element",
  7: "critical_hit",
  8: "critical_hit_defense",
  9: "hit_rate",
  10: "evasion_rate",
  11: "attack",
  12: "defense",
  13: "exp",
  14: "loot_id",
  16: "category",
  19: "model_id",
  21: "talk_id",
  22: "seller_id",
  26: "respawn_time",
  28: "aggro_range",
}

MONSTER_SCHEMA = RecordSchema(
  name="monster_data",
  headers=(Column("field_count", I32),),  # = 32
  columns=tuple(Column(_NAMED.get(i, f"field_{i}"), I64) for i in range(32)),
)

register_schema(
  "dat",
  MONSTER_SCHEMA,
  type_names=("SealOnline MonsterDataFile",),
  versions=(12,),
)
