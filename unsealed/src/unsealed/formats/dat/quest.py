"""QuestFile body decoder -- the NPC dialog tree (despite the name).

Header: 64-byte title + int32 count = number of dialog NODES. Each
node is one fixed record, read in full (no boundary guessing):

    metadata     : group_id, talk_id (int32 x2)
    conditions   : int32 x12 -- availability gates (below)
    parent_idx   : int32 -- talk_id of the parent node (0 = root)
    player       : int32 len + EUC-KR text -- the player's choice line
                   ("\\0" for a pure NPC line / the group header)
    npc          : int32 count + count x (len + text) -- the NPC reply,
                   one text per "click Next" page
    action_id    : int32 -- global, monotonic index into an external
                   action/script table (set respawn, change job, ...);
                   -1 = terminal, 0 = none
    consequences : int32 x18 -- effects applied on reaching the node

Nodes sharing a group_id form one NPC's dialog; talk_id 0 is a
non-displayed per-group header. The tree is built from parent_idx.

Start node: roots are the parent_idx==0 nodes (excluding talk_id 0).
When a group has several they are condition-gated, and the engine
takes the FIRST root (ascending talk_id) whose conditions all pass --
the unconditional root is the fallback. E.g. group 234: tid1 needs
flag 51 + level 50, tid2 needs flag 51, tid5 needs an item, tid6 is
the catch-all.

conditions (all must hold to show the node): has_item_0/1 (id) +
min_item_*_count, has_flag (flag.dat id), has_job, min_reputation,
min_level, min_days, min_cegel, time_of_day (hour, 1..31).
consequences (applied on reach): reward_item_0/1/2 (id) + _count
(signed: + give / - take), set_flag (flag.dat id; negative = clear),
reward_cegel/exp/fame, teleport_map_id, change_job_id, add_skill_ids,
revival_point_id. has_flag/set_flag join flag.dat and the item ids
join item.dat.
"""

from ...assets.dat import DatFile
from ...utils.file import File
from .registry import DatBody, register


class QuestBody(DatBody):
  type_name = "Seal Online QuestFile"
  versions = (3,)

  def decode(self, file: File, dat: DatFile) -> None:
    talks = []
    for i in range(dat.count):
      talks.append(self.read(file))
    dat.elements = talks

  def read(self, file: File) -> object:
    node = {}
    node["metadata"] = self.read_metadata_blob(file)
    node["conditions"] = self.read_conditions_blob(file)
    node["parent_idx"] = file.read_int()
    node["player"] = self.read_basic_text_node(file)
    node["npc"] = self.read_basic_text_node_with_count(file)
    node["action_id"] = file.read_int()
    node["consequences"] = self.read_consequence_blob(file)
    return node

  def read_basic_text_node(self, file: File) -> str:
    text_length = file.read_int()
    return file.read(text_length).decode("euc_kr", "replace")

  def read_basic_text_node_with_count(self, file: File) -> list[str]:
    text_count = file.read_int()
    texts = []
    for _ in range(text_count):
      texts.append(self.read_basic_text_node(file))
    return texts

  def read_consequence_blob(self, file: File) -> object:
    node = {}
    consequences = [
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
    ]
    for consequence in consequences:
      node[consequence] = file.read_int()
    return node

  def read_metadata_blob(self, file: File) -> object:
    node = {}
    metadata = [
      "group_id",
      "talk_id",
    ]
    for meta in metadata:
      node[meta] = file.read_int()
    return node

  def read_conditions_blob(self, file: File) -> object:
    node = {}
    conditions = [
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
    ]
    for condition in conditions:
      node[condition] = file.read_int()
    return node


register(QuestBody())
