"""Stone_Step config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="stone_step",
    columns=(
      Column("id", I32),  # the map key
      Column("stone_type", I32),  # 1-BASED in the file
      Column("step", I32),  # 1-BASED in the file
      Column("material_0_item_id", I32),
      Column("material_0_count", I32),
      Column("material_1_item_id", I32),
      Column("material_1_count", I32),
      Column("field_7", I32),  # 10000; rate-shaped, unread
      Column("field_8", I32),  # 1; unread
      Column("cost", I32),
    ),
  ),
  patterns=(r"^Stone_Step$",),
)
