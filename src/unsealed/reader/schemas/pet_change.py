"""Pet evolution table (`p_change.scr`) -- text twin of `PetChangeTable`."""

from ..formats.celltable import i32s
from ..formats.records import Column, I32, RecordSchema, register_schema

PET_CHANGE_SCHEMA = RecordSchema(
  name="pet_change",
  headers=(Column("row_count", I32),),
  columns=(
    Column("source_pet_id", I32),
    Column("result_pet_id", I32),
    Column("cost", I32),
  )
  + i32s(*(f"material_{i}" for i in range(1, 25)))
  + (
    Column("result_prob_cumulative", I32),
    Column("recipe_group", I32),
  ),
)

register_schema("scr", PET_CHANGE_SCHEMA, patterns=(r"^p_change",))
