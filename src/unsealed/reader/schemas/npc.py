"""NPC placement (`npc*.scr`) as a schema.

Header (npc_count, row_count); each row is

    ? | ID | n | (x, y, d) * n

? unknown, ID the NPC id, n the number of instances of the same NPC,
(x, y) the map coordinate, d the facing direction.
"""

from ..formats.celltable import group, i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

NPC_SCHEMA = RecordSchema(
  name="npc",
  headers=(Column("npc_count", I32), Column("row_count", I32)),
  columns=i32s("unknown", "id", "count")
  + (group("instances", ("x", "y", "direction"), count_field="count"),),
)

register_schema("scr", NPC_SCHEMA, patterns=(r"^npc",))
