"""Option_Cost config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="option_cost",
    columns=(
      Column("id", I32),  # 1..count, unique
      Column("item_id", I32),
      Column("option_step", I32),  # 0..4, per-item
      Column("cost", I32),
    ),
  ),
  patterns=(r"^Option_Cost$",),
)
