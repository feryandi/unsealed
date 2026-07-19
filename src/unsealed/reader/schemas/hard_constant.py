"""Hard_Constant config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="hard_constant",
    columns=(
      Column("id", I32),  # the map key
      Column("field_1", I32),  # unread
      Column("field_2", I32),  # unread
      Column("field_3", I32),  # unread
      Column("field_4", I32),  # the one value that is read
    ),
  ),
  patterns=(r"^Hard_Constant$",),
)
