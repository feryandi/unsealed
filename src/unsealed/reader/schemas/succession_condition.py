"""Succession_Condition config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="succession_condition",
    columns=(
      Column("id", I32),  # the map key, 1..4
      Column("range_min", I32),
      Column("range_max", I32),
      Column("field_3", I32),  # 3 / 4; copied, never read
    ),
  ),
  patterns=(r"^Succession_Condition$",),
)
