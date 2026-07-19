"""Reward_Time config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="reward_time",
    columns=(
      Column("id", I32),  # 1..18
      Column("group", I32),  # 1..4; elapsed_seconds restarts per group
      Column("elapsed_seconds", I32),  # multiples of 1800 (30 min steps)
      Column("item_id", I32),  # inferred: item band, consistent per time slot
      Column("count", I32),  # inferred
    ),
  ),
  patterns=(r"^Reward_Time$",),
)
