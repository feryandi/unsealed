"""exbox_exchange config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="exbox_exchange",
    columns=(
      Column("id", I32),  # the map key; both rows are fetched by a literal id
      Column("cost_item_id", I32),
      Column("cost_count", I32),
      Column("item_id", I32),
      Column("field_4", I32),
    ),
  ),
  patterns=(r"^exbox_exchange$",),
)
