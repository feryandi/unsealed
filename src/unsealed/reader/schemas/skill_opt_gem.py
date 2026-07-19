"""Skill_Opt_Gem config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="skill_opt_gem",
    columns=(
      Column("id", I32),  # the map key, 0..55
      Column("gem_type", I32),
      Column("opt_type", I32),
      Column("grade", I32),
      Column("field_4", I32),  # a strict function of grade; money-shaped, unread
      Column("field_5", I32),  # 0 on every grade-0 gem
      # three (value, threshold) pairs
      Column("value_0", I32),
      Column("threshold_0", I32),  # constant 15
      Column("value_1", I32),
      Column("threshold_1", I32),  # constant 40
      Column("value_2", I32),
      Column("threshold_2", I32),  # constant 70
      Column("field_12", I32),
      Column("field_13", I32),  # constant 8
    ),
  ),
  patterns=(r"^Skill_Opt_Gem$",),
)
