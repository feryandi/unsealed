"""Player skill table (`Seal Online SkillFile v4`, Skill.edt / EDT10003.edt)."""

from ..formats.bytefields import Column, I32, RecordSchema, Str, register_schema

SKILL_FILE_SCHEMA = RecordSchema(
  name="skill_file",
  columns=(
    Column("id", I32),
    Column("name", Str(36)),
  )
  + tuple(Column(f"field_{i}", I32) for i in range(10, 104)),
)

register_schema(
  "dat",
  SKILL_FILE_SCHEMA,
  type_names=("Seal Online SkillFile",),
  versions=(4,),
)
