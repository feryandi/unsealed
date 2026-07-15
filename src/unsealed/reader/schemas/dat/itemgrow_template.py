"""Itemgrow_Template config table (`Seal Online Data` container).

Every field is an 8-byte int.
"""

from .base import Column, RecordSchema, I64, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="itemgrow_template",
    columns=tuple(Column(f"field_{i}", I64) for i in range(18)),
  ),
  patterns=(r"^Itemgrow_Template$",),
)
