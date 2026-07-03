"""SkillFile (`Seal Online SkillFile v8`) as a schema.

Record: `int32 id` + null-terminated EUC-KR `name[32]` + 40 stat fields
(a mix of int32 and float, mapped below) + a length-prefixed EUC-KR
`description` (`Pstr`). Records walk exactly `count` to EOF; record 0 is
an all-zero template. Because of the trailing `Pstr` the record is
variable-length, so the schema streams it.

buff_1..4_id join the Buff table; buff_1_chance/durations and the
`*_refine`-style multipliers are float-encoded (see the `_FLOATS` set).
"""

from .base import Column, DataSchema, F32, I32, Pstr, Str, register_type_schema

_STAT_MAP = {
  0: "job_id",
  1: "skill_type",
  2: "prereq_skill_id",
  3: "prereq_skill_level",
  4: "max_skill_level",
  5: "skill_points",
  6: "min_level",
  7: "required_equip_type",
  9: "ap_cost",
  10: "support_subtype",  # 1 = shield/element/party buff, 5 = leadership buff
  11: "cast_num_target",
  12: "area_of_effect",
  13: "cast_range",
  14: "casting_time",
  15: "duration_seconds",
  16: "cooldown_seconds",
  17: "number_of_hits",
  18: "damage_pct",
  19: "element",
  22: "linked_skill_1",
  23: "buff_1_id",
  24: "buff_1_duration_seconds",
  25: "buff_1_chance",
  26: "linked_skill_2",
  27: "buff_2_id",
  28: "buff_2_duration_seconds",
  29: "buff_2_chance",
  30: "buff_3_id",
  31: "buff_4_id",  # float-encoded (int bits decode to a whole buff id)
  34: "icon_id",
  35: "projectile_speed",  # ~1000 ranged magic, 8-15 melee, 1 self/party buff
  36: "reserved",
  38: "ultimate_move_pct",
}

# Stat indices read as IEEE-754 float rather than int32.
_FLOATS = frozenset({14, 15, 16, 25, 28, 31, 38, 39})

_STATS = tuple(
  Column(_STAT_MAP.get(i, f"stat_{i}"), F32 if i in _FLOATS else I32) for i in range(40)
)

SKILL_SCHEMA = DataSchema(
  name="skill",
  columns=(Column("id", I32), Column("name", Str(32))) + _STATS + (Column("description", Pstr),),
)

register_type_schema(SKILL_SCHEMA, "Seal Online SkillFile", (8,))
