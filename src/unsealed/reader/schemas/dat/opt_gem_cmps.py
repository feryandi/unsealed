"""Opt_Gem_Cmps config table (`Seal Online Data` container, columns not yet identified)."""

from .base import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="opt_gem_cmps",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
    ),
  ),
  patterns=(r"^Opt_Gem_Cmps$",),
)
