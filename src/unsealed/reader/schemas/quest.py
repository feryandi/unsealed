"""QuestFile (`Seal Online QuestFile v3`/`v5`) -- the NPC dialog tree -- as
a schema. `count` = number of dialog NODES; each node is one record:

    group_id, talk_id                  metadata
    12 (v3) or 14 (v5) x int32         availability conditions
    parent_idx                         talk_id of the parent (0 = root)
    player            Pstr             the player's choice line
    npc               Array(Pstr)      NPC reply, one Pstr per "Next" page
    action_id                          index into an external action table
    18 (v3) or 19 (v5) x int32         consequences applied on reach

The `npc` field is a count-prefixed list of length-prefixed strings --
the one nested field, expressed with `Array(Pstr)`. Nodes sharing a
group_id form one NPC's dialog; the tree is built from parent_idx.
has_flag/set_flag join flag.dat; item/reward ids join item.dat.

The record layout (not just the header string) is RE'd against the
client's `sub_109fa20` loader (see `schemas/CLAUDE.md`): v5 inserts two
extra condition ints (between min_reputation/min_level and between
min_level/min_days) and one extra consequence int at the tail, present
from v4 on. v4 itself is not registered here (same insertion points,
minus the two v5-only condition ints) since no v4 sample has been seen.
"""

from ..formats.bytefields import Array, Column, RecordSchema, I32, Pstr, register_schema

_CONDITIONS = (
  "has_item_0",
  "min_item_0_count",
  "has_item_1",
  "min_item_1_count",
  "has_flag",
  "has_job",
  "reserved_28",
  "min_reputation",
  "min_level",
  "min_days",
  "min_cegel",
  "time_of_day",
)
_CONSEQUENCES = (
  "reward_item_0",
  "reward_item_0_count",
  "reward_item_1",
  "reward_item_1_count",
  "reward_item_2",
  "reward_item_2_count",
  "set_flag",
  "reward_cegel",
  "reward_exp",
  "reward_fame",
  "reserved_12",
  "reserved_13",
  "reserved_14",
  "reserved_15",
  "teleport_map_id",
  "change_job_id",
  "add_skill_ids",
  "revival_point_id",
)

QUEST_SCHEMA = RecordSchema(
  name="quest",
  columns=(
    (Column("group_id", I32), Column("talk_id", I32))
    + tuple(Column(n, I32) for n in _CONDITIONS)
    + (
      Column("parent_idx", I32),
      Column("player", Pstr),
      Column("npc", Array(Pstr)),
      Column("action_id", I32),
    )
    + tuple(Column(n, I32) for n in _CONSEQUENCES)
  ),
)

register_schema(
  "dat",
  QUEST_SCHEMA,
  type_names=("Seal Online QuestFile",),
  versions=(3,),
)

# v5: two extra condition ints spliced into the v3 block (min_reputation,
# <new>, min_level, <new>, min_days -- proven by the loader's version-gated
# copy at 0x109fb90/0x109fba5, only taken when esi(version) >= 5) and one
# extra consequence int appended at the tail (0x109fe99, gated on
# version >= 4, so v5 also gets it). Neither new field has an identified
# consumer -- the loader only copies them -- so they stay positional.
_CONDITIONS_V5 = (
  "has_item_0",
  "min_item_0_count",
  "has_item_1",
  "min_item_1_count",
  "has_flag",
  "has_job",
  "reserved_28",
  "min_reputation",
  "field_17",
  "min_level",
  "field_20",
  "min_days",
  "min_cegel",
  "time_of_day",
)
_CONSEQUENCES_V5 = _CONSEQUENCES + ("field_37",)

QUEST_V5_SCHEMA = RecordSchema(
  name="quest_v5",
  columns=(
    (Column("group_id", I32), Column("talk_id", I32))
    + tuple(Column(n, I32) for n in _CONDITIONS_V5)
    + (
      Column("parent_idx", I32),
      Column("player", Pstr),
      Column("npc", Array(Pstr)),
      Column("action_id", I32),
    )
    + tuple(Column(n, I32) for n in _CONSEQUENCES_V5)
  ),
)

register_schema(
  "dat",
  QUEST_V5_SCHEMA,
  type_names=("Seal Online QuestFile",),
  versions=(5,),
)
