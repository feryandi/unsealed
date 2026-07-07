"""Schemas for pipe-delimited `.scr` tables.

The machinery (typed `Column`s, `CellCursor`, `RecordSchema`, the
table/list guard) is shared in `..celltable`; here we only register the
`|`-delimited built-ins. Columns are fully typed -- the schema, not
runtime int-or-string guessing, decides each token's type. Callers may
also pass their own `RecordSchema`.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union

from ..formats.celltable import group, i32s
from ..formats.records import REGISTRY, Column, I32, RecordSchema

_FMT = "scr"


def register_schema(schema: RecordSchema, patterns: Tuple[str, ...] = ()) -> None:
  REGISTRY.register(schema, _FMT, patterns=patterns)


def get_schema(schema: Union[str, RecordSchema, None]) -> Optional[RecordSchema]:
  return REGISTRY.get(_FMT, schema)


def schema_for_filename(stem: str) -> Optional[RecordSchema]:
  return REGISTRY.for_filename(_FMT, stem)


# ── built-in schemas (current client format, per tests/output) ──

# Item drop table: header row_count; each row is repeated (item_id,
# drop_rate) pairs to the end of the line. Identified by row index (id =
# row), which monster.dat references (a monster's loot field -> drop row N).
register_schema(
  RecordSchema(
    name="drop",
    headers=(Column("row_count", I32),),
    columns=(group("drops", ("item_id", "drop_rate")),),
    index_field="id",
  ),
  patterns=(r"^drop",),
)

# NPC placement: header (npc_count, row_count); each row is
#   ? | ID | n | (x, y, d) * n
# ? unknown, ID the NPC id, n the number of instances of the same NPC,
# (x, y) the map coordinate, d the facing direction.
register_schema(
  RecordSchema(
    name="npc",
    headers=(Column("npc_count", I32), Column("row_count", I32)),
    columns=i32s("unknown", "id", "count")
    + (group("instances", ("x", "y", "direction"), count_field="count"),),
  ),
  patterns=(r"^npc",),
)

# Map object placement (m22/m32/...): header (unknown, total_count,
# row_count); each row is  ID | n | (x, y) * n  -- one object id and its n
# placements on the map. (Older 2018 m-maps used a 2-line header; this is
# the current client's 3-line form.)
register_schema(
  RecordSchema(
    name="map_object",
    headers=(Column("unknown", I32), Column("total_count", I32), Column("row_count", I32)),
    columns=i32s("id", "count")
    + (group("positions", ("x", "y"), count_field="count"),),
  ),
  patterns=(r"^m\d",),
)

# Warp/teleport points (warp/worp): header row_count; each row is 3 ints
# (semantics not yet identified -> field_N placeholders).
register_schema(
  RecordSchema(
    name="warp",
    headers=(Column("row_count", I32),),
    columns=i32s("field_0", "field_1", "field_2"),
  ),
  patterns=(r"^warp", r"^worp"),
)


# `{name: schema}` of this format's built-ins (snapshot, after registration).
SCR_SCHEMAS = REGISTRY.by_format(_FMT)

# Re-exported for callers/tests that referenced these names on this module.
__all__ = [
  "SCR_SCHEMAS",
  "get_schema",
  "register_schema",
  "schema_for_filename",
]
