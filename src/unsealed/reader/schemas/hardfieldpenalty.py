"""HardFieldpenalty config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

PENALTY_COLUMNS = (
  Column("id", I32),  # the map key -- but rows are found by (col 1, col 3)
  Column("penalty_group", I32),
  Column("field_2", I32),
  Column("job_id", I32),
  # an 11-slot penalty array
  *(Column(f"penalty_{i}", I32) for i in range(11)),
  Column("option_id_0", I32),  # 83 -- the option-id space Rank uses
  Column("message_id_0", I32),  # 3099 -- string-table id
  Column("option_id_1", I32),  # 84
  Column("message_id_1", I32),  # 3100
  Column("field_19", I32),
  Column("field_20", I32),
)

register_schema(
  "dat",
  RecordSchema(name="hardfieldpenalty", columns=PENALTY_COLUMNS),
  patterns=(r"^HardFieldpenalty$",),
)
