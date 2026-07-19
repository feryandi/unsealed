"""Bonus_Result config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="bonus_result",
    columns=(
      Column("field_0", I32),  # unread; == 1 on the only row
      # any-of, scanned against the inventory; -1 = empty slot
      Column("accepted_item_id_0", I32),
      Column("accepted_item_id_1", I32),
      Column("accepted_item_id_2", I32),
      Column("item_id", I32),
      Column("field_5", I32),  # read -> sent to the server as packet 0x647c3's arg
      Column("required_count", I32),
      Column("field_7", I32),
      Column("field_8", I32),
      Column("field_9", I32),
      Column("field_10", I32),
    ),
  ),
  patterns=(r"^Bonus_Result$",),
)
