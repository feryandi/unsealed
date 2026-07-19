"""Pet_Breed config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="pet_breed",
    columns=(
      Column("id", I32),  # the map key, 1..10
      Column("value", I32),  # meaning differs per row
    ),
  ),
  patterns=(r"^Pet_Breed$",),
)
