"""Rose-currency price coefficient (`rose_coefficient.scr`) as a schema.

A count header then `id | coefficient` rows -- a per-id float multiplier
applied to the "rose flower" (장미꽃) cash-shop price (the currency the
item-trade-mall lists, see `item_trade_mall`). Row 0 is the zero
placeholder every Seal count-table carries.
"""

from ..formats.records import Column, F32, I32, RecordSchema, register_schema

ROSE_COEFFICIENT_SCHEMA = RecordSchema(
  name="rose_coefficient",
  headers=(Column("row_count", I32),),
  columns=(
    Column("id", I32),
    Column("coefficient", F32),
  ),
)

register_schema("scr", ROSE_COEFFICIENT_SCHEMA, patterns=(r"^rose_coefficient",))
