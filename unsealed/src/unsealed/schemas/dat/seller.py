"""SellerFile (`Seal Online SellerFile v1`) as a schema.

One extra int32 (`header_extra` = 30, the slot count), then `count`
records of 30 int32 item-id slots (`field_0..field_29`). Each record is
one shop; the slots are a zero-terminated list of item ids it sells (the
"stop at the first 0" compaction is client-side now). The record id is
the row index.
"""

from .base import Column, DataSchema, I32, register_type_schema

SELLER_SCHEMA = DataSchema(
  name="seller",
  header_extra=1,
  index_field="id",
  columns=tuple(Column(f"field_{i}", I32) for i in range(30)),
)

register_type_schema(SELLER_SCHEMA, "Seal Online SellerFile", (1,))
