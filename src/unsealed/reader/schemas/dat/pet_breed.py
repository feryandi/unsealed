"""Pet_Breed config table (`Seal Online Data` container, columns not yet identified)."""

from .base import Column, DataSchema, I32, register_data_schema

register_data_schema(
  DataSchema(
    name="pet_breed",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
    ),
  ),
  patterns=(r"^Pet_Breed$",),
)
