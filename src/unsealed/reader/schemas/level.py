"""LevelDataFile (`Seal Online LevelDataFile v1`) as a schema."""

from ..formats.bytefields import Column, I64, RecordSchema, register_schema

LEVEL_SCHEMA = RecordSchema(
  name="level",
  index_field="level",  # the record index is the level
  columns=(Column("experience_points", I64),),
)

register_schema(
  "dat",
  LEVEL_SCHEMA,
  type_names=("Seal Online LevelDataFile",),
  versions=(1,),
  patterns=(r"^level$",),  # kept so the GUI schema picker still finds it by name
)
