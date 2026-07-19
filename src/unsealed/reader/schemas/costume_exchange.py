"""costume_exchange config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="costume_exchange",
    columns=(
      Column("id", I32),  # 1..136, sequential -- NOT the lookup key
      Column("field_1", I32),
      Column("item_id", I32),
      Column("result_item_id", I32),
      Column("result_count", I32),
    ),
  ),
  patterns=(r"^costume_exchange$",),
)
