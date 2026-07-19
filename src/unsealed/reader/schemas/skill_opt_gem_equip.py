"""Skill_Opt_Gem_Equip config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="skill_opt_gem_equip",
    columns=(
      Column("id", I32),  # the map key, 0..4 -- the tier
      Column("field_1", I32),  # 100..300, rises with id
      Column("field_2", I32),  # 3.5M..50M, rises with id; probably a cost
    ),
  ),
  patterns=(r"^Skill_Opt_Gem_Equip$",),
)
