"""Buff description table (`buffdesc.edt` -> `.scr`)."""

from ..formats.celltable import Text
from ..formats.records import Column, I32, RecordSchema, register_schema

BUFFDESC_SCHEMA = RecordSchema(
  name="buffdesc",
  headers=(Column("row_count", I32),),
  columns=(
    Column("id", I32),
    Column("category", I32),
    Column("field_2", I32),
    Column("key_b", I32),
    Column("effect_key", Text),
    Column("animation", Text),
    Column("field_6", I32),
    Column("field_7", I32),
    Column("description_params", Text),
    Column("field_9", Text),
    Column("field_10", Text),
    Column("key_c", I32),
    Column("key_d", I32),
    Column("field_13", I32),
  ),
)

register_schema("scr", BUFFDESC_SCHEMA, patterns=(r"^buffdesc",))
