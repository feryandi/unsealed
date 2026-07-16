"""Skill_Opt_Gem_Equip config table.

A `Seal Online Data` container; columns are not yet identified.
"""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="skill_opt_gem_equip",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
    ),
  ),
  patterns=(r"^Skill_Opt_Gem_Equip$",),
)
