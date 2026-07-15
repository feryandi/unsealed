"""Skill_Opt_Type_Str config table (`Seal Online Data` container, columns not yet identified)."""

from .base import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="skill_opt_type_str",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
    ),
  ),
  patterns=(r"^Skill_Opt_Type_Str$",),
)
