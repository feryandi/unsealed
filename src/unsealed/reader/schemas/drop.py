"""Item drop table (`drop*.scr`) as a schema.

Header row_count; each row is repeated (item_id, drop_rate) pairs to the
end of the line. Identified by row index (id = row), which monster.dat
references (a monster's loot field -> drop row N).
"""

from ..formats.celltable import group
from ..formats.records import Column, I32, RecordSchema, register_schema

DROP_SCHEMA = RecordSchema(
  name="drop",
  headers=(Column("row_count", I32),),
  columns=(group("drops", ("item_id", "drop_rate")),),
  index_field="id",
)

register_schema("scr", DROP_SCHEMA, patterns=(r"^drop",))
