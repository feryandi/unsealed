"""NPC ambient-dialogue table (`npctalk.tsv`) as a schema.

Rows of `kind | text | npc_name | weight` -- the shopkeeper/vendor chatter
lines. The opening `BEGIN <count>` marker row reads as `kind="BEGIN"`,
`text=<count>`; the data rows are `kind="TALK"`. `weight` is the line's
selection frequency.
"""

from ..formats.celltable import Text
from ..formats.records import Column, I32, RecordSchema, register_schema

NPCTALK_SCHEMA = RecordSchema(
  name="npctalk",
  columns=(
    Column("kind", Text),
    Column("text", Text),
    Column("npc_name", Text),
    Column("weight", I32),
  ),
)

register_schema("tsv", NPCTALK_SCHEMA, patterns=(r"^npctalk",))
