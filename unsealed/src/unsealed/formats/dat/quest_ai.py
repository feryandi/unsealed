"""QuestFile body decoder -- despite the name, this is the NPC
dialog tree. Decodes the WHOLE file (all NPCs / sub-trees).

Layout (v3): shared 64-byte header + int32 count (= total number
of dialog NODES across all NPCs); records start at offset 68.

The file is a FLAT STREAM of variable-size records. Each
talk/choice/answer-pool record embeds its owning dialog id at
group_id@+76 and a sequential talk_id@+80; a run of records with
the same group_id is one conversation "group". The first NPC opens
with a 74-byte header (int32 group_id + a 70-byte root_blob); every
later group boundary is absorbed as an ordinary record (see below),
so the walk never needs to special-case it.

    record :=
      talk   (149 + text)  an NPC line. 19 int32 flags, group_id@76,
                           talk_id@80, 14 int32, pad byte@140, then
                           int32 `a`@141 + int32 len@145 + text. `a`
                           is a PAGE COUNT: a-1 "click Next"
                           continuation pages follow as bare {int32
                           len, text} records (no header). An empty
                           talk (len 1, text NUL) is how a new group/
                           NPC opens -- its 150 bytes are the old
                           end_blob+id+root_blob folded into one
                           record, so grouping by group_id "just
                           works".
      choice (140 + text)  a player option. 19 int32, group_id@76,
                           talk_id@80, 12 int32, parent talk_id@132,
                           int32 len@136 + text.
      answer               the NPC reply to the preceding choice:
        - short: int32 flag + int32 len + text, where `flag` is a
                 PAGE COUNT (flag-1 continuation pages follow), OR
        - pool:  an empty marker (flag=1, len=1, text=NUL) then a
                 VARIABLE run of talk records (each its own 149-byte
                 layout + pages) -- the conditional NPC outcomes --
                 until the next choice or a group boundary. Conditions
                 live in the members' numbered fields: "29"@+112 =
                 min_reputation, "32"@+124 = cegel cost. The game picks
                 the matching outcome. The run may be empty.

Note: talk, cond_answer AND choice share the same field block, so any
of them can carry the condition fields (min_reputation @+112,
min_cegel @+124). "talk" vs "cond_answer" is only WHERE the record
sits (a cond_answer is a talk inside a choice's answer pool); a choice
just gates whether that option is shown/selectable.

Record type at the cursor: byte@140 is 0x00 (the talk pad) => talk,
else (printable) => choice. A new group is simply where group_id@+76
changes. The int32 flag fields are surfaced verbatim as numbered
keys for later RE: they encode CONSEQUENCES (cegel cost / +/- money
/ warp-map id) and availability CONDITIONS (quest-flag / fame /
level gating). field "1" on a choice is a global monotonic edge
index (-1 = terminal).
"""

import struct

from ...assets.dat import DatFile
from ...utils.file import File
from .registry import DatBody, register

_TEXT_LEN_MAX = 8192  # sanity bound on a single record's text length
_NUL = chr(0)  # an empty talk / answer-pool marker decodes to this


class QuestBody(DatBody):
  type_name = "Seal Online QuestFile"
  versions = (3,)

  def decode(self, file: File, dat: DatFile) -> None:
    size = file.size
    # The first NPC opens with a bare int32 id + 70-byte root_blob;
    # later boundaries fold into an empty-talk record, so this is the
    # only place we skip a header explicitly.
    file.read_int()
    self.read_root_text_node(file)

    groups = []
    current = None
    stopped = None
    self._prev = None
    while file.pointer + 80 <= size:
      gid = self._peek_int(file, 76)
      if gid is None:
        break
      if current is None or gid != current["group_id"]:
        current = {"kind": "group", "group_id": gid, "nodes": []}
        groups.append(current)
      if not self.read_node(file, current["nodes"], gid):
        stopped = {"reason": "desync", "offset": file.pointer}
        break

    dat.elements = groups
    dat.unknown["groups_decoded"] = len(groups)
    dat.unknown["nodes_decoded"] = sum(len(g["nodes"]) for g in groups)
    dat.unknown["stopped"] = stopped

  def _emit(self, node: dict, nodes: list) -> None:
    """Append a node, handing its leading field "1" back to the PREVIOUS
    node as that reply's `action_id`.

    Field "1" is the action_id the engine runs as the CONSEQUENCE of the
    previous reply (set respawn, change job, ...). It is stored at the
    HEAD of this record but belongs to the node before it, so we move it
    there as we go -- no second pass. -1 = terminal, 0 = nothing.
    Answers and continuation pages have no field "1" (so the reply
    before them keeps action_id 0); the last reply of a group takes its
    action_id from the next group's boundary record's "1" (or 0 at EOF)
    -- i.e. the leading int of the "end_blob"/boundary handed back to
    that reply."""
    action = node.pop("1", None)
    if action is not None and self._prev is not None:
      self._prev["action_id"] = action
    node.setdefault("action_id", 0)
    self._prev = node
    nodes.append(node)

  # -- node dispatch --------------------------------------------------

  def read_node(self, file: File, nodes: list, gid: int) -> bool:
    lead = self._peek_byte(file, 140)
    if lead is None:
      return False
    if lead < 0x20:
      node = self.read_text_node(file)
      if node["text_length"] >= _TEXT_LEN_MAX:
        return False
      self._emit(node, nodes)
      return self._read_pages(file, nodes, node["a"])
    choice = self.read_choice_node(file)
    if choice["text_length"] >= _TEXT_LEN_MAX:
      return False
    self._emit(choice, nodes)
    return self.read_answer_node(file, nodes, gid)

  def _read_pages(self, file: File, nodes: list, page_count: int) -> bool:
    """Read the page_count-1 "click Next" continuation pages that
    trail a multi-page talk or answer."""
    for _ in range(max(0, page_count - 1)):
      page = self.read_next_page(file)
      if page["text_length"] >= _TEXT_LEN_MAX:
        return False
      self._emit(page, nodes)
    return True

  def read_answer_node(self, file: File, nodes: list, gid: int) -> bool:
    node = {"kind": "answer"}
    node["flag"] = file.read_int()
    node["text_length"] = file.read_int()
    if node["text_length"] >= _TEXT_LEN_MAX:
      return False
    node["text"] = file.read(node["text_length"]).decode("euc_kr", "replace")
    self._emit(node, nodes)
    if node["text"] == _NUL:
      # Empty marker -> variable-length answer pool: the run of talk
      # records (each its own 149-byte layout + pages) in this group,
      # until the next choice or a group boundary. Members are the
      # conditional NPC outcomes -- gated by min_reputation / min_cegel
      # (named fields). The run may be empty (a bare "no reply" choice).
      while self._peek_byte(file, 140) == 0 and self._peek_int(file, 76) == gid:
        member = self.read_text_node(file, "cond_answer")
        if member["text_length"] >= _TEXT_LEN_MAX:
          return False
        self._emit(member, nodes)
        if not self._read_pages(file, nodes, member["a"]):
          return False
    else:
      # `flag` is a page count, like a talk's `a`.
      return self._read_pages(file, nodes, node["flag"])
    return True

  # -- peek helpers (look ahead without advancing the stream) ---------

  def _peek_int(self, file: File, offset: int):
    data = file.seek(offset + 4)
    if len(data) < offset + 4:
      return None
    return struct.unpack_from("<I", data, offset)[0]

  def _peek_byte(self, file: File, offset: int):
    data = file.seek(offset + 1)
    if len(data) < offset + 1:
      return None
    return data[offset]

  # -- record readers -------------------------------------------------

  def read_root_text_node(self, file: File) -> object:
    node = {"kind": "root_blob"}
    for i in range(1, 16):
      node[str(i)] = file.read_int()
    node["pad"] = file.read(1)
    node["a"] = file.read_int()
    node["b"] = file.read_int()
    node["pad"] = file.read(1)
    return node

  # Named fields shared by talk, cond_answer (a pool-member talk) and
  # choice. Two blocks, both still partly numbered pending RE:
  #   * leading block (fields 1-19) = CONSEQUENCES applied when this
  #     node is reached -- give/take items + exp/fame/cegel rewards.
  #   * block after talk_id (fields 22-35) = availability CONDITIONS.
  # reward_*_count is signed: negative = take/consume, positive = give.
  _NAMED_FIELDS = {
    # consequences (leading block)
    2: "reward_item_0",
    3: "reward_item_0_count",
    4: "reward_item_1",
    5: "reward_item_1_count",
    6: "reward_item_2",
    7: "reward_item_2_count",
    9: "reward_cegel",
    10: "reward_exp",
    11: "reward_fame",
    # conditions (block after talk_id)
    22: "has_item_0",
    23: "min_item_0_count",
    24: "has_item_1",
    25: "min_item_1_count",
    26: "has_flag",
    27: "has_job",
    29: "min_reputation",
    30: "min_level",
    31: "min_days",
    32: "min_cegel",
    33: "time_of_day",
    34: "parent_talk_id",
  }

  def read_text_node(self, file: File, kind: str = "talk") -> object:
    node = {"kind": kind}
    for i in range(1, 20):
      node[self._NAMED_FIELDS.get(i, str(i))] = file.read_int()
    node["group_id"] = file.read_int()
    node["talk_id"] = file.read_int()
    for i in range(22, 36):
      node[self._NAMED_FIELDS.get(i, str(i))] = file.read_int()
    node["pad"] = file.read(1)
    node["a"] = file.read_int()
    node["text_length"] = file.read_int()
    node["text"] = file.read(node["text_length"]).decode("euc_kr", "replace")
    return node

  def read_choice_node(self, file: File) -> object:
    node = {"kind": "choice"}
    for i in range(1, 20):
      node[self._NAMED_FIELDS.get(i, str(i))] = file.read_int()
    node["group_id"] = file.read_int()
    node["talk_id"] = file.read_int()
    for i in range(22, 34):
      node[self._NAMED_FIELDS.get(i, str(i))] = file.read_int()
    node["parent_id"] = file.read_int()
    node["text_length"] = file.read_int()
    node["text"] = file.read(node["text_length"]).decode("euc_kr", "replace")
    return node

  def read_next_page(self, file: File) -> object:
    """A "click Next" continuation page: bare {len, text}, no header."""
    node = {"kind": "next_page"}
    node["text_length"] = file.read_int()
    node["text"] = file.read(node["text_length"]).decode("euc_kr", "replace")
    return node


register(QuestBody())
