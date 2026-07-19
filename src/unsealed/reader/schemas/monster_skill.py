"""Monster-skill assignment table (`Seal Online MonsterSkill v1`, Skill_Mon.edt)."""

from ..formats.bytefields import Column, I32, RecordSchema, register_schema

MONSTER_SKILL_SCHEMA = RecordSchema(
  name="monster_skill",
  columns=(
    Column("id", I32),
    Column("field_1", I32),
    Column("field_2", I32),
    Column("field_3", I32),
    Column("field_4", I32),
    Column("skill_type", I32),
    Column("skill_id_or_value", I32),
    Column("field_7", I32),
    Column("field_8", I32),
    Column("monster_id", I32),
    Column("field_10", I32),
  ),
)

register_schema(
  "dat",
  MONSTER_SKILL_SCHEMA,
  type_names=("Seal Online MonsterSkill",),
  versions=(1,),
)
