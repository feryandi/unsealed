"""Pet feed item table (`p_feed.scr`) as a schema.

A count header then rows keyed by `pet_id` followed by a run of item ids
(the items that pet type will eat). The item-id run stays `field_N` --
only the leading key is named. Row 0 is the zero placeholder.
"""

from ..formats.celltable import i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

PET_FEED_SCHEMA = RecordSchema(
  name="pet_feed",
  headers=(Column("row_count", I32),),
  columns=(Column("pet_id", I32),) + i32s(*(f"field_{i}" for i in range(1, 33))),
)

register_schema("scr", PET_FEED_SCHEMA, patterns=(r"^p_feed",))
