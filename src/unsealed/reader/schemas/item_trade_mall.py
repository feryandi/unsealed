"""Cash-shop listing table (`itemtrademall.scr`) as a schema.

A count header then one row per cash-shop entry:

    visible | category_id | category_en | category_kr | product_id |
    item_id | item_name | f7 | f8 | f9 | fa | fb | currency | price

`item_id` is the granted item; `product_id` is the shop's own slot id;
`currency` is the payment item's display name (e.g. 장미꽃, "rose flower")
and `price` its cost. The middle `f*` columns stay unlabelled.
"""

from ..formats.celltable import Text, i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

ITEM_TRADE_MALL_SCHEMA = RecordSchema(
  name="item_trade_mall",
  headers=(Column("row_count", I32),),
  columns=(
    Column("visible", I32),
    Column("category_id", I32),
    Column("category_en", Text),
    Column("category_kr", Text),
    Column("product_id", I32),
    Column("item_id", I32),
    Column("item_name", Text),
  )
  + i32s("field_7", "field_8", "field_9", "field_10", "field_11")
  + (
    Column("currency", Text),
    Column("price", I32),
  ),
)

register_schema("scr", ITEM_TRADE_MALL_SCHEMA, patterns=(r"^itemtrademall",))
