"""Schemas for tab-delimited `.tsv` tables.

A `.tsv` is a generic tab-separated Seal table: no header count line, the
`id` is the first column, and a row may MIX int and string cells. It reuses
the shared cell-table machinery in `..celltable` (typed `Column`s,
`CellCursor`, `RecordSchema`); only the tab delimiter and these built-in
schemas are `.tsv`-specific.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union

from ..formats.celltable import Text, i32s
from ..formats.records import REGISTRY, Column, RecordSchema

_FMT = "tsv"


def register_schema(schema: RecordSchema, patterns: Tuple[str, ...] = ()) -> None:
  REGISTRY.register(schema, _FMT, patterns=patterns)


def get_schema(schema: Union[str, RecordSchema, None]) -> Optional[RecordSchema]:
  return REGISTRY.get(_FMT, schema)


def schema_for_filename(stem: str) -> Optional[RecordSchema]:
  return REGISTRY.for_filename(_FMT, stem)


# Guarder spawn table: id | field_1 | field_2 | field_3 | model name.
# The last column is a text actor/model name (e.g. "GF_bycart").
register_schema(
  RecordSchema(
    name="guarder",
    columns=i32s("id", "field_1", "field_2", "field_3") + (Column("model", Text),),
  ),
  patterns=(r"^guarder",),
)

# Polymorph stat table: id + 11 int fields (semantics not yet identified).
register_schema(
  RecordSchema(
    name="polymorph",
    columns=i32s("id", *(f"field_{i}" for i in range(1, 12))),
  ),
  patterns=(r"^polymorph",),
)


# `{name: schema}` of this format's built-ins (snapshot, after registration).
TSV_SCHEMAS = REGISTRY.by_format(_FMT)

__all__ = [
  "TSV_SCHEMAS",
  "get_schema",
  "register_schema",
  "schema_for_filename",
]
