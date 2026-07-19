"""Compose_Template config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="compose_template",
    columns=(
      Column("id", I32),
      Column("field_1", I32),
      Column("field_2", I32),  # 25000000; cost-shaped, unread
      Column("field_3", I32),
      Column("item_id", I32),
      Column("min_required", I32),  # floor: `cmp; jge` or the dialog rejects
      Column("field_6", I32),
      Column("field_7", I32),
      Column("field_8", I32),
      # how many (item_id, count) pairs follow; the record is variable-length
      Column("material_count", I32),
      Column("material_0_item_id", I32),
      Column("material_0_count", I32),
    ),
  ),
  patterns=(r"^Compose_Template$",),
)
