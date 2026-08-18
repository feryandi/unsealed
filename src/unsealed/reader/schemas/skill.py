"""SkillFile (`Seal Online SkillFile v8`, and the unrelated `Seal Online
Data v13` `skill.dat`) as a schema.

## v8 (`SKILL_SCHEMA`)

Record: `int32 id` + null-terminated EUC-KR `name[32]` + 40 stat fields
(a mix of int32 and float, mapped below) + a length-prefixed EUC-KR
`description` (`Pstr`). Records walk exactly `count` to EOF; record 0 is
an all-zero template. Because of the trailing `Pstr` the record is
variable-length, so the schema streams it.

buff_1..4_id join the Buff table; buff_1_chance/durations and the
`*_refine`-style multipliers are float-encoded (see the `_FLOATS` set).
"""

from ..formats.bytefields import (
  Column,
  RecordSchema,
  F32,
  I32,
  Pstr,
  Str,
  register_schema,
)

_STAT_MAP = {
  0: "job_id",
  1: "skill_type",
  2: "prereq_skill_id",
  3: "prereq_skill_level",
  4: "max_skill_level",
  5: "skill_points",
  6: "min_level",
  7: "required_equip_type",
  9: "ap_cost",
  10: "support_subtype",  # 1 = shield/element/party buff, 5 = leadership buff
  11: "cast_num_target",
  12: "area_of_effect",
  13: "cast_range",
  14: "casting_time",
  15: "duration_seconds",
  16: "cooldown_seconds",
  17: "number_of_hits",
  18: "damage_pct",
  19: "element",
  22: "linked_skill_1",
  23: "buff_1_id",
  24: "buff_1_duration_seconds",
  25: "buff_1_chance",
  26: "linked_skill_2",
  27: "buff_2_id",
  28: "buff_2_duration_seconds",
  29: "buff_2_chance",
  30: "buff_3_id",
  31: "buff_4_id",  # float-encoded (int bits decode to a whole buff id)
  34: "icon_id",
  35: "projectile_speed",  # ~1000 ranged magic, 8-15 melee, 1 self/party buff
  36: "reserved",
  38: "ultimate_move_pct",
}

# Stat indices read as IEEE-754 float rather than int32.
_FLOATS = frozenset({14, 15, 16, 25, 28, 31, 38, 39})

_STATS = tuple(
  Column(_STAT_MAP.get(i, f"stat_{i}"), F32 if i in _FLOATS else I32) for i in range(40)
)

SKILL_SCHEMA = RecordSchema(
  name="skill",
  columns=(Column("id", I32), Column("name", Str(32)))
  + _STATS
  + (Column("description", Pstr),),
)

register_schema(
  "dat",
  SKILL_SCHEMA,
  type_names=("Seal Online SkillFile",),
  versions=(8,),
)

# --- v13 (`SKILL_V13_SCHEMA`) -----------------------------------------------
#
# `out/skill.dat` is a DIFFERENT, unrelated container: a `Seal Online Data
# v13` file, not a `Seal Online SkillFile v8` one -- `_STAT_MAP` above (a
# different client's `id + name[32] + 40 stats + Pstr description` layout)
# does not apply to it, and neither schema is a version of the other; they
# just happen to both describe "skill" data from different client builds.
#
# Unlike its uniform-int32-grid siblings in the `Seal Online Data` family
# (`job_type.edt`, `Combat_power.edt`, ...) this record is a genuine mix of
# byte-precise fields -- proven by tracing the actual loader, not guessed
# from the data.
#
# RE'd against `tests/input/so3d2026.memorydump.txt` (ImageBase `0x400000`
# -- a DIFFERENT build than the rest of `schemas/CLAUDE.md`'s `0xcc0000`-
# based addresses; see [[so3d-memorydump-re]] for `redump.py`). The string
# `"skill\skill.dat"` (`0xdab618`) only leads to a filename/CRC integrity
# table, not the parser -- a dead end. The real path is via RTTI: class
# `SkillTable` (`redump.py rtti --list`), chased through the mangled-name ->
# TypeDescriptor -> RTTICompleteObjectLocator -> vtable chain to `0xdabd5c`,
# whose ctor use in the ROW loader is `CSealTableManager::LoadSkillTable
# Internal` (`sub_c392e0`, debug string at `0xdac6dc`).
#
# That loader walks ONE byte cursor through the record field-by-field with
# NO de-interleaving -- unlike most tables here, the columns are already in
# file order, so the loader IS the schema, straight off `func 0xc392e0`:
#
#     +0    id                 int32
#     +4    name               255-byte buffer (`sub_ca1570(dest,src,0xff)`)
#                               -- NOT a multiple of 4. Every other fixed
#                               string in this codebase pads to 4 bytes;
#                               this one genuinely doesn't, which is why
#                               `bytefields.Str` no longer requires it
#                               (`cells` returns None for an odd size,
#                               opting the column out of the int32-cell
#                               fast path instead of raising).
#     +259  field_2..field_4   3 x int32
#     +271  key                32-byte buffer -- an internal slug
#                               ("SkillSleep", "SkillMACombo",
#                               "SkillTSCombo", "SkillFireTick"), the same
#                               role as `buffdesc.py`'s `effect_key`
#     +303  field_5..field_17  13 x int32, all read into the row node
#     +355  field_18..field_20 3 x float32 (`movss`, confirmed by the
#                               instruction, not inferred from the data)
#     +367  field_21..field_24 4 x int32
#     +383  (52 bytes)         13 x int32 the cursor SKIPS -- `add edx,0x28;
#                               add eax,0xc`, no read/store between. Real
#                               per-row data (2025/4645 rows nonzero in the
#                               sample), just unread by this build -- the
#                               identical "unread tail" shape `monster.py`
#                               documents for its fields 23..31.
#     +435  field_38..field_40 3 x int32
#     +447  (4 bytes)          1 more skipped, unread int32
#     +451  field_42..field_43 2 x float32 (`movss`)
#     +459  field_44           int32
#     +463  description        512-byte buffer (`sub_ca1570`, len=0x200)
#
# `+463 + 512 = 975` -- the exact per-record size the file's own
# `count`/`field_count` header implies (and the field tally above sums to
# exactly the header's declared `field_count=47`, which is corroboration,
# not proof -- `field_count` is not authoritative, per `DataTableBody`'s
# docstring). `id`/`name`/`key`/`description` are proven by what the
# loader's copy structurally does with them. Row 0 is the all-zero
# placeholder, `name` literally `"skill"`.
#
# The row's C++ layout is independently confirmed by its CONSTRUCTOR, not
# just the loader: `sub_c20110` (the ctor `LoadSkillTableInternal` calls
# per record) zero-inits every member at an EXPLICIT `row+offset`, one
# `mov`/`movss` per field (`row+8`, `+0x110`, `+0x114`, `+0x140`, ...,
# `+0x19c`, then a 512-byte block at `+0x1a0`, then `+0x3a0`). Converting
# every `field_N`'s file-cursor destination to a `row+offset` and diffing
# against this list matches EXACTLY, member for member, including two
# fields the file stores far apart but the C++ struct keeps adjacent:
# `field_23` (file `+375`) lands at `row+0x14c`, immediately before
# `field_38` (file `+435`, 60 bytes later in the file) at `row+0x150` --
# strong independent confirmation the byte-cursor trace above is right.
#
# **Repeated ids are per-LEVEL rows, not a decode bug or a per-class
# duplicate (an earlier pass here guessed "job classes share a row" --
# wrong; corrected below).** `id` is not a unique row key: id 5 ("Martial
# Combo") repeats 5 times, id 6 ("Great Sword Combo") 3 times, and across
# the whole file every repeated-id run has length 1, 5, 10, 15, or 20 --
# clean level-cap tiers, not an arbitrary count. This is PROVEN, not just
# a size coincidence: the client stores each skill id's rows behind a
# SEPARATE class, `SkillTables` (plural -- distinct from this row's own
# `SkillTable`, singular), found via `CSO3D`'s skill-resolve routine
# (`sub_9b7c40`, whose own error strings name it: `"Failed To Find Skill
# ID : %d"`, `"Failed To Find Skill Level : %d"`,
# `"Failed To Find USkill ID : %d"`). For each of the player's learned
# skills it looks up `SkillTables` by id in the `0x75`/`0x76` container
# (`sub_6e7050`, the same map-find every table here uses), RTTI-checks the
# result with `__RTDynamicCast` to `SkillTables*` (mangled name at
# `0xeacdbc`), then treats `SkillTables_obj + 8` as a vector: a size check
# (`sub_9ba2f0`, logs "Failed To Find Skill Level" when too small) followed
# by an INDEXED element fetch (`sub_9b63e0(vec, level)`) that returns one
# `SkillTable*` -- i.e. one of these 975-byte rows. The level number itself
# is the vector INDEX, not a field inside the row; nothing in this record
# stores "which level is this" explicitly.
#
# **This build's client code never fetches a skill row by the generic
# `CSealTableManager::GetTableElem` path.** Every one of `GetTableElem`'s
# (`sub_c261e0`, proven by its own debug string
# `"CSealTableManager::GetTableElem"`) 446 call sites was checked
# byte-precisely for its `type` argument (not just grepped -- disassembling
# blindly backward from an arbitrary call site desyncs on x86's variable
# instruction length, so the check reads the exact `push`/`call` bytes);
# NONE pass `0x75` or `0x76`. The only other consumer found,
# `sub_c260e0`, is reached from just one caller (`sub_7b94b0`) with
# HARDCODED skill ids (255, 319) gated on an event-mode flag -- a one-off
# special case, not a general accessor. So beyond resolving `id` -> the
# `SkillTables` array (`sub_9b7c40` copies only the resolved row's `id`,
# confirming `row+8` = `id` a THIRD way, independent of the loader and the
# ctor), no traced client code reads any individual stat field by name.
# That is consistent with the extensive client/server split documented
# throughout `schemas/CLAUDE.md` (`hard_constant.py`, `level.py`,
# `compose_template.py`, ...) -- the numbers most likely get validated and
# applied server-side, which is why they stay `field_N` rather than being
# guessed at.
#
# **Two data-only naming attempts were tried against `field_4`
# (`Column`s below) and REJECTED / left unresolved, in the same spirit as
# `hardfieldpenalty.py`'s falsified reading -- recorded so nobody retries
# them:**
#   * `field_4` (`+267`) is mostly 0, but its nonzero values (32, 328, 148,
#     48, 190, 191, ...) all fall inside this file's own 1..362 skill-id
#     range, which looks exactly like `prereq_skill_id` (`_STAT_MAP[2]` in
#     the v8 schema above). **Checked and REJECTED**: id 32 is "Blazing
#     Hurricane"; the skills whose `field_4` is 32 include "Fireball",
#     "Frostbolt", "Intimidation", "Defense Guard" -- unrelated basic
#     skills across different skill families, not plausible prerequisites
#     of an advanced-sounding skill. In-range is not proof; this is a
#     coincidence of the id space being small.
#   * `field_3` (`+263`) has a clean small range (0..11, unlike `field_4`'s
#     spread), and its `=6` bucket is entirely support/buff-sounding
#     skills ("Intimidation", "Enrage", "Defense Guard", "Infinity Guard",
#     "Party Enrage", "Party Urge", "Divine Force", "Acceleration", "Wind
#     Rush") -- suggestive of `skill_type` (`_STAT_MAP[1]`), the same way
#     `buffdesc.py`'s `category` groups by source class. Left `field_3`,
#     not proven: no consumer reads it, and one coherent bucket out of a
#     0..11 range is a much weaker signal than the `(category, key_b)`
#     composite-key proof `buffdesc.py` has for its own grouping column.
#
# `skill01.dat`..`skill23.dat` and `uskill.dat`/`uskill01.dat`..
# `uskill23.dat` are the same layout with exactly one fewer `field_N` in
# the `+303` block (12 slots, not 13 -- 971-byte records) -- see
# `skill_file.py`, which holds that sibling schema.

SKILL_V13_SCHEMA = RecordSchema(
  name="skill_v13",
  columns=(
    Column("id", I32),
    Column("name", Str(255)),
    Column("job_type", I32),
    Column("skill_type", I32),
    Column("field_4", I32),
    Column("key", Str(32)),
  )
  + tuple(Column(f"field_{i}", I32) for i in range(5, 18))  # +303, 13 fields
  + tuple(Column(f"field_{i}", F32) for i in range(18, 21))  # +355, 3 floats
  + tuple(Column(f"field_{i}", I32) for i in range(21, 25))  # +367, 4 fields
  + tuple(Column(f"field_{i}", I32) for i in range(25, 38))  # +383, 13 unread
  + tuple(Column(f"field_{i}", I32) for i in range(38, 41))  # +435, 3 fields
  + (Column("field_41", I32),)  # +447, 1 unread
  + tuple(Column(f"field_{i}", F32) for i in range(42, 44))  # +451, 2 floats
  + (Column("field_44", I32), Column("description", Str(512))),  # +459, +463
)

register_schema(
  "dat",
  SKILL_V13_SCHEMA,
  patterns=(r"^skill$",),
  versions=(13,),
)
