"""Warp/teleport points (`warp*.scr` / `worp*.scr`) as a schema.

Header row_count; each row is 3 ints (semantics not yet identified ->
field_N placeholders).
"""

from ..formats.celltable import i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

WARP_SCHEMA = RecordSchema(
  name="warp",
  headers=(Column("row_count", I32),),
  columns=i32s("field_0", "field_1", "field_2"),
)

register_schema("scr", WARP_SCHEMA, patterns=(r"^warp", r"^worp"))
