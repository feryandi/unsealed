"""Rank config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="rank",
    columns=(
      Column("id", I32),  # 0..5
      Column("rank", I32),  # the map key
      Column("range_min", I32),
      Column("range_max", I32),
      Column("effect_id", I32),  # -> the buff descriptor's first field
      # values, keyed by the option-id table at 0x11a8d68 (scrambled order)
      Column("opt_79", I32),
      Column("opt_80", I32),
      Column("opt_81", I32),
      Column("opt_82", I32),
      Column("opt_78", I32),
      Column("opt_83", I32),
      Column("opt_84", I32),
      Column("opt_1349", I32),
      Column("opt_1350", I32),
      Column("opt_1351", I32),
      Column("field_15", I32),  # used against 0x628; not identified
    ),
  ),
  patterns=(r"^Rank$",),
)
