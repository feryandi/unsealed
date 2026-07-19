"""Monster AI behaviour table (`Seal Online MonsterAI v3`, AI_Mon.edt).

Fixed 136-byte records = 34 int32, no field_count header (records start
right after the count). `id` is contiguous 1..count -- AI behaviour
definitions a monster references, not one row per monster.
"""

from ..formats.bytefields import Column, I32, RecordSchema, register_schema

MONSTER_AI_SCHEMA = RecordSchema(
  name="monster_ai",
  columns=(Column("id", I32),) + tuple(Column(f"field_{i}", I32) for i in range(1, 34)),
)

register_schema(
  "dat",
  MONSTER_AI_SCHEMA,
  type_names=("Seal Online MonsterAI",),
  versions=(3,),
)
