"""Buff description table (`buffdesc*.scr`) as a schema.

A 3-line header (two unidentified counts, then row_count), then rows
mixing ints with text cells (the buff's name, its animation and three
further strings); the unidentified numerics stay `field_N`.
"""

from ..formats.celltable import Text
from ..formats.records import Column, I32, RecordSchema, register_schema

BUFFDESC_SCHEMA = RecordSchema(
  name="buffdesc",
  headers=(
    Column("unknown", I32),
    Column("unknown", I32),
    Column("row_count", I32),
  ),
  columns=(
    Column("id", I32),
    Column("field_1", I32),
    Column("field_2", I32),
    Column("field_3", I32),
    Column("name", Text),
    Column("animation", Text),
    Column("field_6", I32),
    Column("field_7", I32),
    Column("field_8", Text),
    Column("field_9", Text),
    Column("field_10", Text),
    Column("field_11", I32),
    Column("field_12", I32),
    Column("field_13", I32),
  ),
)

register_schema("scr", BUFFDESC_SCHEMA, patterns=(r"^buffdesc",))
