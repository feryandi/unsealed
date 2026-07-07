"""QuestFile (`Seal Online QuestFile v3`) -- the NPC dialog tree -- as a
schema. `count` = number of dialog NODES; each node is one record:

    group_id, talk_id                  metadata
    12 x int32                         availability conditions
    parent_idx                         talk_id of the parent (0 = root)
    player            Pstr             the player's choice line
    npc               Array(Pstr)      NPC reply, one Pstr per "Next" page
    action_id                          index into an external action table
    18 x int32                         consequences applied on reach

The `npc` field is a count-prefixed list of length-prefixed strings --
the one nested field, expressed with `Array(Pstr)`. Nodes sharing a
group_id form one NPC's dialog; the tree is built from parent_idx.
has_flag/set_flag join flag.dat; item/reward ids join item.dat.
"""

from .base import Array, Column, DataSchema, I32, Pstr, register_type_schema

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

QUEST_SCHEMA = DataSchema(
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

register_type_schema(QUEST_SCHEMA, "Seal Online QuestFile", (3,))
