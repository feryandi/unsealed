"""Itemgrow_Template config table (`Seal Online Data` container).

Every field is an 8-byte int.
"""

from .base import Column, DataSchema, I64, register_data_schema

register_data_schema(
  DataSchema(
    name="itemgrow_template",
    columns=tuple(Column(f"field_{i}", I64) for i in range(18)),
  ),
  patterns=(r"^Itemgrow_Template$",),
)
