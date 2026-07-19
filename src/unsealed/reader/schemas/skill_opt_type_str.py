"""Skill_Opt_Type_Str config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="skill_opt_type_str",
    columns=(
      Column("opt_type", I32),  # the map key, 0..13
      Column("message_id", I32),  # AbilityGemMessageTable -> a message/name id
    ),
  ),
  patterns=(r"^Skill_Opt_Type_Str$",),
)
