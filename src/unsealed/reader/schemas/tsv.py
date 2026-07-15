"""Schemas for tab-delimited `.tsv` tables.

A `.tsv` is a generic tab-separated Seal table: no header count line, the
`id` is the first column, and a row may MIX int and string cells. It reuses
the shared cell-table machinery in `..celltable` (typed `Column`s,
`CellCursor`, `RecordSchema`) and the shared `register_schema`; only the
tab delimiter and these built-in schemas are `.tsv`-specific.
"""

from __future__ import annotations

from ..formats.celltable import Text, i32s
from ..formats.records import Column, RecordSchema, register_schema

# Guarder spawn table: id | field_1 | field_2 | field_3 | model name.
# The last column is a text actor/model name (e.g. "GF_bycart").
register_schema(
  "tsv",
  RecordSchema(
    name="guarder",
    columns=i32s("id", "field_1", "field_2", "field_3") + (Column("model", Text),),
  ),
  patterns=(r"^guarder",),
)

# Polymorph stat table: id + 11 int fields (semantics not yet identified).
register_schema(
  "tsv",
  RecordSchema(
    name="polymorph",
    columns=i32s("id", *(f"field_{i}" for i in range(1, 12))),
  ),
  patterns=(r"^polymorph",),
)
