"""Pet_material config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

_PAIRS = tuple(
  col
  for i in range(10)
  for col in (
    Column(f"material_{i}_item_id", I32),
    Column(f"material_{i}_count", I32),
  )
)

register_schema(
  "dat",
  RecordSchema(
    name="pet_material",
    columns=(
      Column("id", I32),  # 1..58, sequential
      Column("item_id", I32),  # the map key, unique, item-id band
      Column("min_required", I32),  # threshold: pet item's +8 < this -> rejected
    )
    + _PAIRS,
  ),
  patterns=(r"^Pet_material$",),
)
