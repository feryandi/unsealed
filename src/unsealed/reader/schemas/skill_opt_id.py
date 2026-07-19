"""Skill_Opt_ID config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="skill_opt_id",
    columns=(
      Column("gem_type", I32),
      Column("opt_id", I32),  # the map key, unique per row
    ),
  ),
  patterns=(r"^Skill_Opt_ID$",),
)
