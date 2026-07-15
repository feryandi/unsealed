"""Buff table (`Seal Online Buff v2`) as a declarative schema.

Fixed 68-byte records: `int32 id` + null-terminated EUC-KR `name[40]` +
6 trailing fields. `id` -> `name` is the lookup SkillFile's buff_1..4_id
point into. Field 1 is a float (round-millisecond duration); the rest
are int32, still unlabelled (see the shape notes in git history).
"""

from .base import Column, RecordSchema, F32, I32, Str, register_schema

BUFF_SCHEMA = RecordSchema(
  name="buff",
  columns=(
    Column("id", I32),
    Column("name", Str(40)),
    Column("field_0", I32),
    Column("duration_ms", F32),  # field 1
    Column("field_2", I32),
    Column("field_3", I32),
    Column("field_4", I32),
    Column("field_5", I32),
  ),
)

register_schema(
  "dat",
  BUFF_SCHEMA,
  type_names=("Seal Online Buff",),
  versions=(2,),
)
