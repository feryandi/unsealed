"""SellerFile (`Seal Online SellerFile v1`) as a schema.

One more int32, `field_count` (= 30, the slot count), then `count`
records of 30 int32 item-id slots (`field_0..field_29`). Each record is
one shop; the slots are a zero-terminated list of item ids it sells (the
"stop at the first 0" compaction is client-side now). The record id is
the row index.
"""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

SELLER_SCHEMA = RecordSchema(
  name="seller",
  headers=(Column("field_count", I32),),  # = 30
  index_field="id",
  columns=tuple(Column(f"pos_{i}_item_id", I32) for i in range(30)),
)

register_schema(
  "dat",
  SELLER_SCHEMA,
  type_names=("Seal Online SellerFile",),
  versions=(1,),
)
