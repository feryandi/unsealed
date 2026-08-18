"""Monster AI tables: the client's `Seal Online MonsterAI` (`AI_Mon.edt`)
and the server's `crt_ai.scr` -- two different formats for what is
structurally the same "AI behaviour profile" concept.

`AI_MON_SCHEMA` (`.dat`/`.edt`): fixed 136-byte records = 34 int32, no
field_count header (records start right after the count). `id` is
contiguous 1..count -- AI behaviour definitions a monster references, not
one row per monster. Unnameable from the so3d client dump: `AI_Mon.edt`
has no filename string there at all, so the client never loads it and the
columns cannot be named from that side (see `schemas/CLAUDE.md`).

`CRT_AI_SCHEMA` (`.scr`): the SERVER's own copy, reverse-engineered
directly from the Linux game server binary `ggg_all2` (`tests/input/
servers-2018/.../ggg_all2.disasm.txt` + the raw ELF, which has full
string/section tables the client dump lacks). Its loader
(`CRT_set_ai_script`) and two independent runtime consumers were traced by
address, which is why this schema's names are proven rather than guessed
-- see `schemas/CLAUDE.md` for the full derivation. One AI profile:

    id | field_1 | pass_chance | (skill_type, weight) * 6 | (trigger) * 3

`pass_chance` plus the six `skill_N_weight` values sum to exactly 100 in
the sample data (2111/3447 rows), and the runtime AI tick does a single
`rand() % 100` roll against a running cumulative sum of exactly these
fields (`pass_chance` first, then each pair in order) to pick which
`skill_N_type` to use this tick -- a classic weighted-random
skill-selection table, not a guess. `pass_chance == -1` (36 rows) makes
that roll never land in range, i.e. an explicit "no weighted picks, only
triggers" profile -- those rows have all-zero skill pairs and a populated
trigger instead. An independent third-party server reimplementation (a
clean-room C++ parser the user supplied mid-session, not sourced from this
dump) reads the same 33 columns as one dead `id` slot + 7 uniform
`(skill_type, weight)` picks + 3 six-field `trigger`s -- arithmetically
identical to this schema (its pick 0 is exactly `field_1, pass_chance`
fused into one slot with an implicit `skill_type=0` "do nothing"
sentinel), but NOT how `ggg_all2` actually lays the record out in memory:
this binary's own jump table proves cells 0 and 1 are both discarded
(never copied anywhere) and `pass_chance` lands at a struct offset well
outside the contiguous 6-pair array, not inside a 7th pair. Kept as 1 dead
field + 1 scalar + 6 pairs here because that is what THIS binary's
disassembly proves; the other project's field names for the trigger struct
(`trigger_type`, `parameter`, `cooldown_ms`, `max_uses`, `fire_chance`) are
adopted below for the five trigger cells this dump's own loader never
reads back. That naming is no longer just plausible-and-free: sample row
3366 carries `trigger_1 = (type=4, parameter=0, cooldown_ms=140000,
max_uses=1, fire_chance=100, skill_type=5629)` -- a 140-second cooldown, a
single use, and a guaranteed proc are exactly what those names predict,
which a coincidence would be unlikely to produce. See `schemas/CLAUDE.md`
for exactly which cells are this dump's own proof versus that borrowed
naming.

**`AI_id` linkage, proven against `monster.scr`** (`tests/input/
servers-2018/.../scripts/monster.scr`, not schema'd here -- only this one
column was traced): its loader (`CRT_set_type_script`, `0x81329c4`) parses
26-int32/104-byte records the same switch-per-cell way as `crt_ai.scr`,
and cell 14 (the row's 15th `|`-field, after its own always-`"a"` leading
id) writes to record offset `0x34`. Both runtime AI-tick consumers
(`0x8139e88`, `0x813b220`) read a monster instance's live type id, index
`monster.scr`'s own table with it, and read THAT SAME offset `0x34` as the
`crt_ai.scr` row to use -- so column 14 of `monster.scr` is `AI_id`. Cross
-checked against real data, not just the offset match: only 61 of 5235
`monster.scr` rows carry a nonzero AI_id (5174 are the default `0`, i.e.
"no scripted AI"), all in `crt_ai.scr`'s populated 1286..2177+ id band, and
every one resolves to a `crt_ai.scr` row with real skill data -- e.g.
`monster.scr` rows 2690-2692 (three `id=200` colour variants) all carry
`AI_id=2174`, and `crt_ai.scr` row 2174 is exactly `pass_chance=0,
skill_1=(type=2312, weight=50)`, a live weighted pick, not a placeholder.

**`skill_N_type`/`trigger_N_skill_type` linkage, proven against
`crt_skill.scr`**: that file's own per-row layout (`id, field_1, field_2,
field_3, field_4, skill_type, skill_id_or_value, field_7, field_8,
monster_id, field_10` -- 11 int32) is the SAME shape `schemas/CLAUDE.md`
already documents for the binary `Skill_Mon.dat`/`monster_skill.py` table,
right down to its own `monster_id` column -- i.e. `crt_skill.scr` is that
table's `.scr` twin, and each row it's indexed by is already tied to one
specific monster. That is why the overwhelming majority of `monster.scr`
rows use `AI_id=0`: a `crt_ai.scr` profile's `skill_N_type` cells are
bespoke references into `crt_skill.scr` rows built for a particular
monster, not a generic reusable skill-id space, so only the handful of
monsters with a hand-authored AI profile carry a nonzero `AI_id` at all.
"""

from ..formats.records import Column, I32, RecordSchema, register_schema

AI_MON_SCHEMA = RecordSchema(
  name="monster_ai",
  columns=(Column("id", I32),) + tuple(Column(f"field_{i}", I32) for i in range(1, 34)),
)

register_schema(
  "dat",
  AI_MON_SCHEMA,
  type_names=("Seal Online MonsterAI",),
  versions=(3,),
)

CRT_AI_SCHEMA = RecordSchema(
  name="crt_ai",
  headers=(Column("row_count", I32),),
  columns=(
    # cells 0/1: read by the loader but never stored (jump-table entries 0
    # and 1 both point straight at the "next cell" label) -- 0 is the row's
    # own id (PROVEN redundant: equal to the row's file position in every
    # sample row) and 1 is always 0 in the sample, so both are dead weight
    # in the file rather than server state.
    Column("id", I32),
    Column("field_1", I32),
    # PROVEN: compared against `rand() % 100` at the top of both runtime AI
    # ticks (`0x8139e88`, `0x813b220`) -- rolls below this land on "use no
    # skill this tick" before any skill_N pair is even considered.
    Column("pass_chance", I32),
  )
  + tuple(
    c
    for i in range(1, 7)
    for c in (
      # PROVEN: bounds-checked at load time against crt_skill.scr's own
      # row count (`CRT_set_ai_script`'s "iSkill_ID error" check) and used
      # as a live index into the server's crt_skill table at runtime on a
      # hit -- a row number in crt_skill.scr, not a raw game skill id.
      # Named `skill_type` (not e.g. `skill_row`) because that is
      # literally what the loader's own error format string calls this
      # exact cell -- "AI_id:%d, id:%d, skill_type:%d" -- not a guess.
      Column(f"skill_{i}_type", I32),
      # PROVEN: the weighted-random bucket width. Walking pass_chance then
      # each skill_N_weight in order with a running cumulative sum and a
      # single 0..99 roll is EXACTLY what both runtime consumers do, and
      # pass_chance + sum(skill_1..6_weight) == 100 on every populated
      # sample row.
      Column(f"skill_{i}_weight", I32),
    )
  )
  + tuple(
    c
    for i in range(1, 4)
    for c in (
      # NOT proven by this dump: the loader copies these into the record
      # but its own validation pass never reads them back (only the 6th
      # cell of each group is checked), so nothing here pins down their
      # individual meaning. Named from the third-party reimplementation's
      # `Trigger` struct (see the module docstring) rather than left
      # `field_N`, since a conditioned/triggered skill (type + a
      # parameter + a cooldown + a use cap + a fire chance) is exactly
      # the shape a "wider skill_N pair" slot alongside the plain
      # weighted picks above would need, and it costs nothing to record
      # pending independent confirmation from this binary.
      Column(f"trigger_{i}_type", I32),
      Column(f"trigger_{i}_parameter", I32),
      Column(f"trigger_{i}_cooldown_ms", I32),
      Column(f"trigger_{i}_max_uses", I32),
      Column(f"trigger_{i}_fire_chance", I32),
      # PROVEN the same way as skill_N_type: the loader's OWN validation
      # names this exact cell in its error format string --
      # "CRT_set_ai_script. Event iSkill_ID error. AI_id:%d, id:%d,
      # skill_type:%d" -- bounds-checked against crt_skill.scr's row count
      # exactly like skill_N_type, just at group-relative offset 5 instead
      # of 0. The third-party source independently calls this same
      # trailing cell `skill_id`, agreeing it is a skill reference.
      Column(f"trigger_{i}_skill_type", I32),
    )
  ),
)

register_schema("scr", CRT_AI_SCHEMA, patterns=(r"^crt_ai$",))
