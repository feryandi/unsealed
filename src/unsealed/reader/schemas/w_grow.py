"""Weapon-growth table (`w_grow.tsv`) as a schema.

Eleven still-unlabelled integer columns per row (growth thresholds/stat
steps); no count header and no proven semantics yet, so
every column stays `field_N`. Row 0 is the zero placeholder.
"""

from ..formats.celltable import i32s
from ..formats.records import RecordSchema, register_schema

W_GROW_SCHEMA = RecordSchema(
  name="w_grow",
  columns=i32s(*(f"field_{i}" for i in range(11))),
)

register_schema("tsv", W_GROW_SCHEMA, patterns=(r"^w_grow",))
