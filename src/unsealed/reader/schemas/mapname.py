"""Map object placement (`m22.scr` / `m32.scr` / ...) as a schema.

Header (unknown, total_count, row_count); each row is

    ID | n | (x, y) * n

-- one object id and its n placements on the map. (Older 2018 m-maps used
a 2-line header; this is the current client's 3-line form.)
"""

from ..formats.celltable import group, i32s
from ..formats.bytefields import Column, RecordSchema, I32, Str, register_schema

MAP_NAME_SCHEMA = RecordSchema(
  name="mapname",
  headers=(),
  columns=(
    Column("field_1", I32),
    Column("name", Str(256)),
    Column("field_4", I32),
    Column("field_5", I32),
    Column("field_6", I32),
    Column("field_7", I32),
    Column("server_map_id", I32),
    Column("field_9", I32),
    Column("field_10", I32),
    Column("field_11", I32),
    Column("field_12", I32),
    Column("field_13", I32),
    Column("map_file", Str(256)),
    Column("field_15", I32),
    Column("npc_file", Str(256)),
    Column("field_17", I32),
    Column("m_file", Str(256)),
    Column("field_19", I32),
    Column("map_num?", Str(256)),
    Column("field_20", I32),
    Column("field_21", I32),
    Column("description", Str(512)),
  ),
)

register_schema("dat", MAP_NAME_SCHEMA, patterns=(r"^mapname$",))
