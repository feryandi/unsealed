"""Mission config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, I64, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="mission",
    columns=(
      Column("id", I32),  # the map key; == the row index
      Column("message_id", I32),  # string-table id (< 3446)
      # two objective groups
      Column("objective_0_type", I32),
      Column("objective_0_target", I32),
      Column("objective_0_count", I32),
      Column("objective_1_type", I32),
      Column("objective_1_target", I32),
      Column("objective_1_count", I32),
      Column("exp", I64),  # cells 8-9; int64 test: 98/105 sign-extended
      Column("field_10", I32),
      Column("field_11", I32),  # up to 379000; money-shaped, unread
      Column("field_12", I32),  # 0 / 28077; item-id band, unread
      Column("field_13", I32),
      Column("field_14", I32),
      Column("field_15", I32),
    ),
  ),
  patterns=(r"^Mission$",),
)
