"""Schemas for interpreting `.scr` rows.

A `.scr` is a line-based table of pipe-delimited integer cells. A schema
names the columns so a raw row becomes a labelled record. It supports:

  - `headers`: names for the leading non-row lines (e.g. version, count)
  - `columns`: fixed leading column names per row
  - `group`:   an optional trailing repeating group of sub-fields,
               either count-driven (a prior column holds the repeat
               count) or fill-to-end (consume the rest of the row)

Built-in schemas are registered below; callers may also pass their own
`ScrSchema` instance. Schemas are matched to files by name/pattern.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

Cell = Union[int, str]


def parse_cell(value: str) -> Cell:
  try:
    return int(value)
  except ValueError:
    return value


@dataclass(frozen=True)
class Group:
  """A repeating group of sub-fields at the end of a row."""

  name: str
  fields: Tuple[str, ...]
  # Column holding the repeat count; None = repeat to fill the row.
  count_field: Optional[str] = None


@dataclass(frozen=True)
class ScrSchema:
  name: str
  headers: Tuple[str, ...] = ()
  columns: Tuple[str, ...] = ()
  group: Optional[Group] = None
  # When set, the row's 0-based index is stored under this name (the row
  # is identified by position, e.g. drop tables referenced by id=row).
  index_field: Optional[str] = None

  def apply_headers(self, lines: List[str]) -> Dict[str, Cell]:
    return {name: parse_cell(val) for name, val in zip(self.headers, lines)}

  def apply_row(self, cells: List[Cell], index: Optional[int] = None) -> Dict[str, Any]:
    rec: Dict[str, Any] = {}
    if self.index_field is not None and index is not None:
      rec[self.index_field] = index
    i = 0
    for col in self.columns:
      rec[col] = cells[i] if i < len(cells) else None
      i += 1

    if self.group is not None:
      g = self.group
      width = len(g.fields)
      if g.count_field is not None and isinstance(rec.get(g.count_field), int):
        reps = rec[g.count_field]
      else:
        reps = (len(cells) - i) // width if width else 0
      items: List[Dict[str, Cell]] = []
      for _ in range(reps):
        if i + width > len(cells):
          break
        items.append({f: cells[i + k] for k, f in enumerate(g.fields)})
        i += width
      rec[g.name] = items

    if i < len(cells):  # anything unaccounted for
      rec["_extra"] = cells[i:]
    return rec


# ── registry ──

SCR_SCHEMAS: Dict[str, ScrSchema] = {}
# (filename-stem regex, schema name) for auto-selection by the pipeline.
_FILENAME_RULES: List[Tuple["re.Pattern[str]", str]] = []


def register_schema(schema: ScrSchema, patterns: Tuple[str, ...] = ()) -> None:
  SCR_SCHEMAS[schema.name] = schema
  for pat in patterns:
    _FILENAME_RULES.append((re.compile(pat, re.IGNORECASE), schema.name))


def get_schema(schema: Union[str, ScrSchema, None]) -> Optional[ScrSchema]:
  if isinstance(schema, ScrSchema):
    return schema
  if isinstance(schema, str):
    return SCR_SCHEMAS.get(schema)
  return None


def schema_for_filename(stem: str) -> Optional[ScrSchema]:
  """The built-in schema whose pattern matches *stem*, if any."""
  for pat, name in _FILENAME_RULES:
    if pat.search(stem):
      return SCR_SCHEMAS[name]
  return None


# ── built-in schemas ──

# Item drop table: line0 = row count; each row is just repeated
#   (item_id, drop_rate) pairs to the end of the line. The drop table is
# identified by its row index (id = row), which monster.dat references
# (e.g. a monster's loot field -> drop row N).
register_schema(
  ScrSchema(
    name="drop",
    headers=("row_count",),
    columns=(),
    group=Group("drops", ("item_id", "drop_rate")),
    index_field="id",
  ),
  patterns=(r"^drop",),
)

# NPC placement: line0 = unknown, line1 = row count; each row is
#   ? | ID | n | (x, y, d) * n
# where ? is unknown, ID is the NPC id, n is the number of instances of
# the same NPC, (x, y) is the map coordinate and d the facing direction.
register_schema(
  ScrSchema(
    name="npc",
    headers=("unknown", "row_count"),
    columns=("unknown", "id", "count"),
    group=Group("instances", ("x", "y", "direction"), count_field="count"),
  ),
  patterns=(r"^npc",),
)
