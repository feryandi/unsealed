"""Pet_Food config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="pet_food",
    columns=(
      Column("id", I32),  # the map key; <- pet_ingest_condition.pet_food_id
      Column("item_id", I32),
      Column("field_2", I32),  # 5/15/30 potency; no observed reader
    ),
  ),
  patterns=(r"^Pet_Food$",),
)
