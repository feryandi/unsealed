"""Sub_G config table (`Seal Online Data` container, columns not yet identified)."""

from .base import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="sub_g",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
      Column("field_3", I32),
      Column("field_4", I32),
      Column("field_5", I32),
      Column("field_6", I32),
    ),
  ),
  patterns=(r"^Sub_G$",),
)
