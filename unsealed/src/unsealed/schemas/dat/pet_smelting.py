"""Pet_smelting config table (`Seal Online Data` container, columns not yet identified)."""

from .base import Column, DataSchema, I32, register_data_schema

register_data_schema(
  DataSchema(
    name="pet_smelting",
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
  patterns=(r"^Pet_smelting$",),
)
