"""Craft/production recipe table (`Seal Online CraftTable File v5`, craft.edt)."""

from ..formats.bytefields import Column, I32, RecordSchema, Str, register_schema

_HEADER = tuple(Column(f"field_{i}", I32) for i in range(10))
_MATERIALS = tuple(
  col
  for i in range(1, 7)
  for col in (
    Column(f"material_{i}_id", I32),
    Column(f"material_{i}_count", I32),
  )
)

CRAFT_TABLE_SCHEMA = RecordSchema(
  name="craft_table",
  columns=(
    Column("id", I32),
    Column("name", Str(256)),
  )
  + _HEADER
  + _MATERIALS,
)

register_schema(
  "dat",
  CRAFT_TABLE_SCHEMA,
  type_names=("Seal Online CraftTable File",),
  versions=(5,),
)
