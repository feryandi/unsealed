"""Option_bit config table.

A `Seal Online Data` container; columns are not yet identified.
"""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="option_bit",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
    ),
  ),
  patterns=(r"^Option_bit$",),
)
