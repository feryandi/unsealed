from ..formats.bytefields import I32, Column, RecordSchema, U32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="level",
    columns=(
      Column("experience_points", U32),
      Column("max_int32_multiplier", I32),
    ),
  ),
  patterns=(r"^level$",),
)
