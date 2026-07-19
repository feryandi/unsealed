"""Attendance_Reward config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="attendance_reward",
    columns=(
      Column("ID", I32),
      Column("day", I32),  # 1..28 within each group
      Column("group", I32),  # 1..2; 28 days each
      Column("reward_item_id", I32),
      Column("reward_amount", I32),
      Column("field_5", I32),
      Column("cummulative_reward_item_id", I32),  # 0 = none
      Column("cummulative_reward_amount", I32),
      Column("field_8", I32),  # constant 1
    ),
  ),
  patterns=(r"^Attendance_Reward$",),
)
