"""Job_type config table (`Seal Online Data` container)."""

from .base import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="job_type",
    columns=(
      Column("job_id", I32),
      Column("field_1", I32),
      Column("field_2", I32),
    ),
  ),
  patterns=(r"^Job_type$",),
)
