"""Compose_Result_Template config table."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="compose_result_template",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
      Column("field_3", I32),
      Column("field_4", I32),
      Column("field_5", I32),
    ),
  ),
  patterns=(r"^Compose_Result_Template$",),
)
