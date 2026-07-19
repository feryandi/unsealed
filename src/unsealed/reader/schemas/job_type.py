"""Job_type config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="job_type",
    columns=(
      Column("id", I32),  # sequential row id; 0 = the skipped dummy row
      Column("job_id", I32),  # the map key: a class id
      Column("combat_power_type", I32),  # 1..9 -> Combat_power.job_type
    ),
  ),
  patterns=(r"^Job_type$",),
)
