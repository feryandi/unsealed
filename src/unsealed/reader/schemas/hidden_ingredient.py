"""Hidden-ingredient recipe table (`hidden_ingredient.tsv`) as a schema.

`id | f1 | f2 | f3 | (item_id, hidden_id) * up-to-10` -- a recipe key, a
few control columns, then the visible ingredient item ids paired with the
hidden reward ids they map to. No count header; row 0 is the zero
placeholder.
"""

from ..formats.celltable import group, i32s
from ..formats.records import RecordSchema, register_schema

HIDDEN_INGREDIENT_SCHEMA = RecordSchema(
  name="hidden_ingredient",
  columns=i32s("id", "field_1", "field_2", "field_3")
  + (group("pairs", ("item_id", "hidden_id")),),
)

register_schema("tsv", HIDDEN_INGREDIENT_SCHEMA, patterns=(r"^hidden_ingredient",))
