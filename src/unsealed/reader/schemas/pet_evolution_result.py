"""New pet-evolution result table (`p_newevolution_result.scr`).

A count header then one row per evolved pet: the resulting item id, its
display name, and four still-unlabelled columns. Row 0 is the zero
placeholder.
"""

from ..formats.celltable import Text, i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

PET_EVOLUTION_RESULT_SCHEMA = RecordSchema(
  name="pet_evolution_result",
  headers=(Column("row_count", I32),),
  columns=(
    Column("item_id", I32),
    Column("name", Text),
  )
  + i32s("field_2", "field_3", "field_4", "field_5"),
)

register_schema(
  "scr", PET_EVOLUTION_RESULT_SCHEMA, patterns=(r"^p_newevolution_result",)
)
