"""Stone_Decomposition config table.

A `Seal Online Data` container; columns are not yet identified.
"""

from .base import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="stone_decomposition",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
      Column("field_3", I32),
      Column("field_4", I32),
      Column("field_5", I32),
      Column("field_6", I32),
      Column("field_7", I32),
      Column("field_8", I32),
      Column("field_9", I32),
      Column("field_10", I32),
      Column("field_11", I32),
      Column("field_12", I32),
      Column("field_13", I32),
    ),
  ),
  patterns=(r"^Stone_Decomposition$",),
)
