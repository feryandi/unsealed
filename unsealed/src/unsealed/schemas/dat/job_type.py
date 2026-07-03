"""Job_type config table (`Seal Online Data` container)."""

from .base import Column, DataSchema, I32, register_data_schema

register_data_schema(
  DataSchema(
    name="job_type",
    columns=(
      Column("job_id", I32),
      Column("field_1", I32),
      Column("field_2", I32),
    ),
  ),
  patterns=(r"^Job_type$",),
)
