"""Pet_smelting config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="pet_smelting",
    columns=(
      Column("id", I32),  # 1..122
      Column("material_id", I32),  # -> pet_material.id; unread
      Column("item_id", I32),  # the map key; -> pet_material.item_id
      Column("field_3", I32),  # 50..5000; unread
      Column("success_text_id", I32),  # string-table id (success message)
      Column("result_item_id", I32),  # the resulting pet's item id
      Column("cost", I32),  # money
    ),
  ),
  patterns=(r"^Pet_smelting$",),
)
