"""Option_bit config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="option_bit",
    columns=(
      Column("id", I32),  # 1..13, sequential -- NOT the lookup key
      Column("option_bit", I32),  # the map key, 0..12
      Column("enabled", I32),
    ),
  ),
  patterns=(r"^Option_bit$",),
)
