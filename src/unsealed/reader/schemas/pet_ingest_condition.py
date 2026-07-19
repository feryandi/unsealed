"""Pet_Ingest_Condition config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="pet_ingest_condition",
    columns=(
      Column("id", I32),  # 1..318, sequential -- NOT the lookup key
      Column("item_id", I32),  # the map key, unique, item-id band
      Column("field_2", I32),  # 1..7 enum; no observed reader
      Column("pet_food_id", I32),
    ),
  ),
  patterns=(r"^Pet_Ingest_Condition$",),
)
