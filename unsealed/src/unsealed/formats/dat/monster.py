"""MonsterDataFile body decoder.

Layout (v12), after the shared 64-byte header + int32 count:

    int32   extra        (= 32 here; meaning TBD)
    record[count]        each 256 bytes = 64 little-endian int32 fields

`field[0]` is the monster id (contiguous 1..count). The other fields are
numeric stats; names are NOT stored here (they live in a separate string
table). Fields are kept raw so they can be labelled incrementally.
"""

import struct

from ...assets.dat import DatFile
from ...utils.file import File
from .registry import DatBody, register

_RECORD_SIZE = 256
_FIELDS = _RECORD_SIZE // 4  # 64 int32 per record
_UNPACK = struct.Struct(f"<{_FIELDS}i")


class MonsterDataBody(DatBody):
  type_name = "SealOnline MonsterDataFile"
  versions = (12,)

  def decode(self, file: File, dat: DatFile) -> None:
    dat.unknown["header_extra"] = file.read_int()

    elements = []
    for _ in range(dat.count):
      fields = _UNPACK.unpack(file.read(_RECORD_SIZE))
      elements.append(
        {
          "id": fields[0],
          "Level": fields[4],
          "HP": fields[6],
          "Movement Speed": fields[8],
          "Attack Range": fields[10],
          "Element": fields[12],
          "Critical Hit": fields[14],
          "Critical Hit Defense": fields[16],
          "Hit Rate": fields[18],
          "Evasion Rate": fields[20],
          "Attack": fields[22],
          "Defense": fields[24],
          "EXP": fields[26],
          "Loot ID": fields[28],
          "?2": fields[30],
          # Category/kind enum. 3 = non-attackable interactive entity
          # (NPCs, gacha machines, warp portals, statues, mailboxes,
          # gift boxes); attackable monsters use other values
          # (0/1/2/6…).
          "Category?": fields[32],
          "?4": fields[34],
          "?5": fields[36],
          "Model ID": fields[38],
          "?7": fields[40],
          # Talk ID -> the NPC dialog tree's npc_id in quest.dat
          # (QuestFile). E.g. nurses 444/445/446/1771 ->
          # 100/101/102/857, all "jucksipja" Red Cross dialogs.
          "Talk ID": fields[42],
          "Seller ID": fields[44],
          "?10": fields[46],
          "?11": fields[48],
          "?12": fields[50],
          # "Monster Name": fields[24],
          # "Loot ID": fields[34],
          # "Type": fields[36],
          # "Post-Death Transformation ID": fields[38],
          # "Summon": fields[40],
          # "Quest ID": fields[44],
          # "Seller ID": fields[46],
          # "AI": fields[48],
          # "Summon ID": fields[50],
          "Respawn Time": fields[52],
          "Aggro Range": fields[56],
          "fields": list(fields),
        }
      )
    dat.elements = elements


register(MonsterDataBody())
