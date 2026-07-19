"""Sub_G config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="sub_g",
    columns=(
      Column("field_0", I32),  # 0..9; the road-map section
      Column("message_id", I32),  # string-table id (< 3446)
      Column("level", I32),  # the map key; == level_min on every row
      Column("field_3", I32),  # 0..4; order within the band
      Column("index", I32),  # == the row index, on every row
      Column("level_min", I32),
      Column("level_max", I32),
    ),
  ),
  patterns=(r"^Sub_G$",),
)
