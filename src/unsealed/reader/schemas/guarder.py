"""Guarder spawn table (`guarder*.tsv`) as a schema.

id | field_1 | field_2 | field_3 | model name. The last column is a text
actor/model name (e.g. "GF_bycart").
"""

from ..formats.celltable import Text, i32s
from ..formats.records import Column, RecordSchema, register_schema

GUARDER_SCHEMA = RecordSchema(
  name="guarder",
  columns=i32s("id", "field_1", "field_2", "field_3") + (Column("model", Text),),
)

register_schema("tsv", GUARDER_SCHEMA, patterns=(r"^guarder",))
