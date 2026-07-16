"""Polymorph stat table (`polymorph*.tsv`) as a schema.

id + 11 int fields (semantics not yet identified -> field_N placeholders).
"""

from ..formats.celltable import i32s
from ..formats.records import RecordSchema, register_schema

POLYMORPH_SCHEMA = RecordSchema(
  name="polymorph",
  columns=i32s("id", *(f"field_{i}" for i in range(1, 12))),
)

register_schema("tsv", POLYMORPH_SCHEMA, patterns=(r"^polymorph",))
