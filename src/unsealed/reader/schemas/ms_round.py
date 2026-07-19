"""Mini-game round table (`MS_Round.scr`) as a schema.

A count header then rows of `id | 300 | n | 0 * 12` -- one mini-game
("MS_*") round: a round id, a duration/limit, a monster count, and a run
of still-unlabelled slot columns (all zero in this client). Row 0 is the
zero placeholder.
"""

from ..formats.celltable import i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

MS_ROUND_SCHEMA = RecordSchema(
  name="ms_round",
  headers=(Column("row_count", I32),),
  columns=(Column("id", I32), Column("field_1", I32), Column("field_2", I32))
  + i32s(*(f"field_{i}" for i in range(3, 15))),
)

register_schema("scr", MS_ROUND_SCHEMA, patterns=(r"^MS_Round",))
