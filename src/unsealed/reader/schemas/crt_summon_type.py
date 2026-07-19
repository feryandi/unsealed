"""Summon-craft cost table (`crt_summon_type.scr`) as a schema.

A count header then rows of `type | (item_id, cost) * up-to-10` -- one
summon/craft type and the item-id + amount pairs it can be produced from,
zero-padded to ten slots. Row 0 is the zero placeholder.
"""

from ..formats.celltable import group
from ..formats.records import Column, I32, RecordSchema, register_schema

CRT_SUMMON_TYPE_SCHEMA = RecordSchema(
  name="crt_summon_type",
  headers=(Column("row_count", I32),),
  columns=(
    Column("type", I32),
    group("costs", ("item_id", "amount")),
  ),
)

register_schema("scr", CRT_SUMMON_TYPE_SCHEMA, patterns=(r"^crt_summon_type",))
