"""Mini-game difficulty multipliers (`MS_difficulty.scr`) as a schema.

A count header then rows of `id | level | float * 7` -- a difficulty tier
and the per-stat scaling factors the mini-game ("MS_*") applies. Row 0 is
the zero placeholder.
"""

from ..formats.records import Column, F32, I32, RecordSchema, register_schema

MS_DIFFICULTY_SCHEMA = RecordSchema(
  name="ms_difficulty",
  headers=(Column("row_count", I32),),
  columns=(
    Column("id", I32),
    Column("level", I32),
    Column("factor_0", F32),
    Column("factor_1", F32),
    Column("factor_2", F32),
    Column("factor_3", F32),
    Column("factor_4", F32),
    Column("factor_5", F32),
    Column("factor_6", F32),
  ),
)

register_schema("scr", MS_DIFFICULTY_SCHEMA, patterns=(r"^MS_difficulty",))
