"""Pet_Decomposition config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="pet_decomposition",
    columns=(
      Column("id", I32),  # 1..238
      Column("item_id", I32),  # the map key, unique, item-id band
      Column("result_item_id", I32),  # constant 26606 = universal pet essence
      Column("result_count", I32),  # 1..25; quantity of result_item_id yielded
    ),
  ),
  patterns=(r"^Pet_Decomposition$",),
)
