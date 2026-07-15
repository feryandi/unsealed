"""Macro_Constant config table.

A `Seal Online Data` container; columns are not yet identified.
"""

from .base import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="macro_constant",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
    ),
  ),
  patterns=(r"^Macro_Constant$",),
)
