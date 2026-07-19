"""Combat_power config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="combat_power",
    columns=(
      Column("id", I32),  # 0 = the skipped dummy row
      Column("job_type", I32),  # the map key; <- Job_type.combat_power_type
      Column("attack_weight", I32),
      Column("hit_weight", I32),
      Column("magic_weight", I32),
      Column("eva_weight", I32),
      Column("defence_weight", I32),
      Column("critical_weight", I32),
      Column("speed_weight", I32),
      Column("move_weight", I32),
      Column("stat_8_divisor", I32),
      Column("stat_9_divisor", I32),
      Column("dmgup_weight", I32),
      Column("dmgdown_weight", I32),
      Column("field_14", I32),
    ),
  ),
  patterns=(r"^Combat_power$",),
)
