"""New pet-evolution material table (`p_newevolution_material.scr`).

A count header then one row per evolvable pet: its item id, display name,
a run of still-unlabelled stat/rate columns, then the money `cost`. Row 0
is the zero placeholder.
"""

from ..formats.celltable import Text, i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

PET_EVOLUTION_MATERIAL_SCHEMA = RecordSchema(
  name="pet_evolution_material",
  headers=(Column("row_count", I32),),
  columns=(
    Column("item_id", I32),
    Column("name", Text),
  )
  + i32s(*(f"field_{i}" for i in range(2, 10)))
  + (
    Column("cost", I32),
    Column("field_11", I32),
  ),
)

register_schema(
  "scr", PET_EVOLUTION_MATERIAL_SCHEMA, patterns=(r"^p_newevolution_material",)
)
