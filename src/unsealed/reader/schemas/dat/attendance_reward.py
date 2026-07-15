"""Attendance_Reward config table.

A `Seal Online Data` container; columns are not yet identified.
"""

from .base import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="attendance_reward",
    columns=(
      Column("ID", I32),
      Column("day", I32),
      Column("field_2", I32),
      Column("reward_item_id", I32),
      Column("reward_amount", I32),
      Column("field_5", I32),
      Column("cummulative_reward_item_id", I32),
      Column("cummulative_reward_amount", I32),
      Column("field_8", I32),
    ),
  ),
  patterns=(r"^Attendance_Reward$",),
)
