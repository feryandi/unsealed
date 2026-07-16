"""Mission config table (`Seal Online Data` container).

field_8 is an 8-byte int (cells 8-9); the rest are int32.
"""

from ..formats.bytefields import Column, RecordSchema, I32, I64, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="mission",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
      Column("field_3", I32),
      Column("field_4", I32),
      Column("field_5", I32),
      Column("field_6", I32),
      Column("field_7", I32),
      Column("field_8", I64),
      Column("field_10", I32),
      Column("field_11", I32),
      Column("field_12", I32),
      Column("field_13", I32),
      Column("field_14", I32),
      Column("field_15", I32),
    ),
  ),
  patterns=(r"^Mission$",),
)
