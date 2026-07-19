"""Hairstyle catalogue (`m_hair1.tsv` / `w_hair1.tsv`) as a schema.

One row per purchasable hairstyle:

    id | f1 | name | price | mesh | tex_count | texture * 6

`mesh` is the base model name and the six `texture_N` columns are its
default plus five colour-variant `.tga`s (r/b/y/g/v). No count header --
the first line is already a data row.
"""

from ..formats.celltable import Text
from ..formats.records import Column, I32, RecordSchema, register_schema

HAIR_SCHEMA = RecordSchema(
  name="hair",
  columns=(
    Column("id", I32),
    Column("field_1", I32),
    Column("name", Text),
    Column("price", I32),
    Column("mesh", Text),
    Column("tex_count", I32),
  )
  + tuple(Column(f"texture_{i}", Text) for i in range(6)),
)

register_schema("tsv", HAIR_SCHEMA, patterns=(r"^[mw]_hair",))
