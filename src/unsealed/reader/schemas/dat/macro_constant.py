"""Macro_Constant config table (`Seal Online Data` container, columns not yet identified)."""

from .base import Column, DataSchema, I32, register_data_schema

register_data_schema(
  DataSchema(
    name="macro_constant",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
    ),
  ),
  patterns=(r"^Macro_Constant$",),
)
