"""Map object placement (`m22.scr` / `m32.scr` / ...) as a schema.

Header (unknown, total_count, row_count); each row is

    ID | n | (x, y) * n

-- one object id and its n placements on the map. (Older 2018 m-maps used
a 2-line header; this is the current client's 3-line form.)
"""

from ..formats.celltable import group, i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

MAP_OBJECT_SCHEMA = RecordSchema(
  name="map_object",
  headers=(
    Column("unknown", I32),
    Column("total_count", I32),
    Column("row_count", I32),
  ),
  columns=i32s("id", "count") + (group("positions", ("x", "y"), count_field="count"),),
)

register_schema("scr", MAP_OBJECT_SCHEMA, patterns=(r"^m\d",))
