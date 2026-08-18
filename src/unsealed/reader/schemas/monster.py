"""MonsterDataFile (`SealOnline MonsterDataFile v12`), and the SERVER's
separate spawn/placement table `monster.scr` -- kept in one module the way
`monster_ai.py` keeps `AI_Mon.edt` next to `crt_ai.scr`, even though this
pair does not share a record shape: `MONSTER_SCHEMA` is the per-SPECIES
combat/display stat sheet a monster's type id looks up (32-36 int64
fields), while `MONSTER_SCR_SCHEMA` is a per-SPAWN configuration row (26
int32 fields) that references a species by id and adds server-only
placement/AI data -- e.g. three sample rows for species 200 (a "colour
variant" set) share `monster_id=200` but each carry a distinct `model_id`.

`MONSTER_SCR_SCHEMA` is reverse-engineered from `ggg_all2`'s
`CRT_set_type_script` (`0x81329c4`) the same way `monster_ai.py`'s
`crt_ai.scr` is -- see `schemas/CLAUDE.md` for the addresses, jump-table
dump, and the cross-file proof that column 14 is `ai_id` (traced all the
way through two independent runtime AI-tick consumers AND cross-checked
against real `crt_ai.scr` data). Only `ai_id`, its rarely-used sibling
`secondary_ai_id` (column 19, bounds-checked against `crt_ai.scr`'s row
count exactly like `ai_id`), and `model_id` (column 12, bounds-checked
against a runtime config value) carry proven-or-strongly-reasoned names;
the rest are `field_N`, annotated with what the loader's own instructions
prove about them (a validated range, a default value, a `* 1000`
seconds-to-milliseconds conversion) even where the GAME meaning is not
recoverable from this trace alone."""

from ..formats.bytefields import Column, RecordSchema, I32, I64, register_schema
from ..formats.celltable import Text

# `element`: 1-based element index (1 Fire, 2 Water, 3 Tree, 4 Steel,
# 5 Earth, 6 Sun, 7 Darkness, 8 Magical, 9 Physical; 0 = none).
# `category`: 3 = non-attackable interactive entity (NPCs, gacha, warp,
# statues...); attackable monsters use other values (0/1/2/6...).
_NAMED = {
  0: "id",
  2: "level",
  3: "hp",
  4: "wander_step_count",
  5: "attack_range",
  6: "element",
  7: "critical_hit_chance",
  8: "critical_hit_defense",
  9: "hit_rate",
  10: "evasion_rate",
  11: "attack",
  12: "defense",
  13: "exp_reward",
  14: "loot_id",
  15: "ai_id",
  16: "category",
  19: "model_id",
  21: "talk_id",
  22: "seller_id",
  23: "pack_flag?",
  24: "secondary_ai_id",
  25: "unique_spawn_flag",
  26: "buff_gold_reward",
  27: "respawn_time",
  28: "spawn_scatter_range",
  29: "call_for_help_range",
  30: "link_flag",
}

MONSTER_SCHEMA = RecordSchema(
  name="monster_data",
  headers=(Column("field_count", I32),),  # = 32
  columns=tuple(Column(_NAMED.get(i, f"field_{i}"), I64) for i in range(32)),
)

register_schema(
  "dat",
  MONSTER_SCHEMA,
  type_names=("SealOnline MonsterDataFile",),
  versions=(12,),
)

MONSTER_V13_SCHEMA = RecordSchema(
  name="monster_data_v13",
  columns=tuple(Column(_NAMED.get(i, f"field_{i}"), I64) for i in range(36)),
)

register_schema(
  "dat",
  MONSTER_V13_SCHEMA,
  patterns=(r"^monster$",),
  versions=(13,),
)

MONSTER_SCR_SCHEMA = RecordSchema(
  name="monster_scr",
  headers=(Column("row_count", I32),),
  columns=(
    # Always the literal letter `"a"` in the sample -- not a number at
    # all -- and, like `crt_ai.scr`/`crt_skill.scr`'s own leading `id`
    # cell, read but never copied into the record (jump-table entry 0
    # points straight at the "next cell" label).
    Column("id", Text),
    # Shared across every "colour variant" spawn row of the same species
    # (e.g. 3 rows all `monster_id=200`, `model_id` 1277/1278/1279) --
    # the species/type id this spawn places, presumably `monster.edt`'s
    # own `id` (`MONSTER_SCHEMA`/`MONSTER_V13_SCHEMA` above), though no
    # cross-file bounds check was found to prove that join directly.
    Column("monster_id", I32),
    # PROVEN: the server-authoritative HP pool -- the value combat damage
    # actually depletes. (An earlier pass here read cell 7, now `hit_rate`,
    # as a second "resource pool" alongside this one -- that reading is
    # retired: cell 7 turned out to be an accuracy stat, not HP-shaped at
    # all. See `hit_rate`'s own comment.) Copied at spawn time to
    # `creature+0x38` (int) AND `creature+0x3c` (float). The full kill
    # sequence is traced in ONE function (`0x8173495`): `creature+0x38 -=
    # damage_arg`; if the result is `<= 0`, set `creature+0x00` to the
    # constant `0x22c4` (a "dead" state code), broadcast a death-shaped
    # event, and route the kill's reward into whichever party member's
    # accumulated damage against this creature is largest. THAT
    # kill-credit check is what nails this cell down specifically: it
    # reads this cell's FLOAT copy (`creature+0x3c`), multiplies by the
    # literal constant `0.3` (VA `0x81f8500`), and compares the result
    # against the credited attacker's own accumulated-damage tracker --
    # i.e. "you need >=30% of this creature's total HP in damage dealt to
    # keep kill credit," which only makes sense if this cell IS the total
    # HP pool. Its huge range (0..515 790 000) fits a large, precise
    # server-side HP number (a large, precise value with none of an
    # accuracy percentage's shape).
    Column("hp_pool", I32),
    # PROVEN: a wander/patrol step count. `0x8137054` (an idle-AI
    # behaviour reached from the same reward handler `loot_id` was found
    # in) reads this cell RAW -- not the loader's own derived
    # boolean+ratio pair (that /1000.0 transform is a real, separate
    # LOADER fact, see `schemas/CLAUDE.md`; this consumer just never
    # reads its output) -- as a loop bound: roll `rand() % 8` for a
    # compass direction, then loop up to this many times trying to step
    # the entity one tile that way (walkability-checked via the same
    # `0x806e440` call `spawn_scatter_range` uses), i.e. a random walk of
    # up to this many steps. Real data is 0..5, matching a small step
    # count far better than it ever matched the loader's `/1000.0` side
    # -computation.
    Column("wander_step_count", I32),
    # PROVEN: attack range. `0x806e7d4` computes `|dx|` and `|dy|` between
    # an attacker and a target, then rejects the attack (returns an error
    # code) unless BOTH `|dx| <= this_cell + 1` and `|dy| <= this_cell +
    # 1` -- a melee-range gate, checked against each side's own cell
    # (attacker's for X, target's for Y in the traced order). Matches
    # `monster.dat`'s own already-proven `attack_range` column in
    # concept, at a different (server-side) offset.
    Column("attack_range", I32),
    # PROVEN: element. Bounds-checked at load time (`0 <= v <= 10`; real
    # data spans exactly 0..9, matching this module's own client-proven
    # 0..9 element enum in `_NAMED`). A damage-calculation function
    # (`0x817b794`) takes two live entities (attacker/defender), looks up
    # EACH one's copy of this cell as an index into its own 11-slot
    # coefficient table (`0x28bd0d48` for one side, the sibling global
    # `0x28bd0d50` for the other), and multiplies both lookups together
    # into the final damage float -- an elemental affinity/resistance
    # matrix keyed by (attacker element, defender element).
    Column("element", I32),
    # REASONED, not fully proven: a percent proc chance, likely critical
    # hit. `0x8060dfc` does `rand() % 100 >= this_cell -> skip`, gating a
    # special-outcome branch that (on success, after a further buff-state
    # check) computes a scaled value and sets a distinct result/event code
    # (`0x7cc9b` on success vs `0x7f33f` on any failure branch) -- the
    # shape of a proc roll with a different outcome message per result.
    # Real data (0..64) fits a percent chance; matches `monster.dat`'s own
    # proven `critical_hit` in concept, though the specific event codes
    # were not traced to a packet/message table to confirm "critical" over
    # some other proc.
    Column("critical_hit_chance", I32),
    # PROVEN, renamed 2026-08-19 from `max_hp`: `0x8060dfc` (the function
    # this cell's dispatcher `0x81403e0` has as its ONE caller) is not a
    # generic skill effect -- it is `GC_ATTACK_CRT2TARGET`, the MONSTER
    # -attacking-A-PLAYER damage formula (confirmed by its wire codes,
    # `0x7f33f`/`0x7cc9b` = `GC_ATTACK_CRT2TARGET_SUCC`/`_CRITICAL`, and by
    # being an early caller of the player-as-defender getter
    # `D_GetPC_Current_Defence`, `0x80b0298`). Its FIRST step is exactly
    # this dispatcher's result, clamped to [20,100] and rolled against
    # `rand()%100` as a hit/miss gate -- i.e. this cell is the monster's
    # own ACCURACY/hit-rate stat, not a resource pool: a higher value
    # means the monster is more likely to land its hit on the player.
    # This reading was cross-checked against an independent RE pass on
    # the same function (a `GC_ATTACK_TO_CRT`-focused damage-formula
    # document already in this repo's history) that landed on the exact
    # same call graph from the opposite direction (working from the
    # wire/packet side in) and named this same step `hit_chance`; the two
    # traces corroborate rather than merely coexist -- see
    # `schemas/CLAUDE.md` for the full writeup and the address
    # cross-references (`0x813fca0`, `0x80b0298`, `0x819814c` all appear
    # in both). Matches `monster.dat`'s own proven `hit_rate` column (its
    # field 9) in concept, at a different, server-side offset -- the same
    # "client display copy vs. server-authoritative value" split already
    # established for `defense`.
    Column("hit_rate", I32),
    # REASONED, not fully proven: a hit-chance penalty for skill/attack
    # accuracy. `0x806626c` computes
    # `clamp(30, 99, GetBuffedStat(attacker) - this_cell + 60)` (the
    # buffed-stat helper, `0x80b0e80`, sums several per-entity buff-slot
    # accumulators -- a "total effective X" getter, X not independently
    # identified). ALL ~17 callers of `0x806626c` (the entire family of
    # element/skill-damage functions this file already documents under
    # `element`) use the SAME shape right before their damage calc: `roll
    # = rand() % 100; if roll >= 0x806626c(...): <miss, skip the damage
    # calc entirely>`. That is unambiguously a hit-chance gate; this cell
    # SUBTRACTS from the buffed stat, so a larger value here means a
    # LOWER chance to hit. Real data (0..3000) is far too large to be a
    # direct percentage itself, consistent with it being combined with a
    # comparably large `GetBuffedStat` result before the `+60`
    # normalization brings the sum back into hit-chance range.
    Column("hit_chance_penalty", I32),
    # PROVEN, renamed 2026-08-19 from `max_ap`: `0x813fca0` is
    # `GC_ATTACK_CRT2TARGET`'s (`0x8060dfc`, see `hit_rate` above)
    # `AttackerPower` term -- the monster's own ATTACK POWER, read right
    # after the hit-chance roll passes, then plugged directly into the
    # raw-damage formula `trunc((AttackerPower*1.3 -
    # (TargetDefense/2.0)*1.7) * 1.1)` (constants confirmed as real
    # `.rodata` doubles), which is then floored at `monster_level * 0.2`
    # (`trunc`, confirmed numerically: 21 rows at level 105 give a floor
    # of exactly 21, matching a well-known player-side claim that a
    # level-105 monster always hits for >= 21 regardless of the
    # defender's Defense). `TargetDefense` here is
    # `D_GetPC_Current_Defence` (`0x80b0298`) -- the PLAYER's defense
    # getter, confirming this whole function is the monster-attacks
    # -player path, not a generic skill effect. This is the direct
    # analogue of a player's `P_Attack`: the same `(100-percent)*value/
    # 100.0` dispatcher shape `hit_rate`/`defense` use (percent-source
    # live-instance offset `+0x114`, divisor `100.0` at VA `0x81f6748`),
    # applied to this cell. Matches `monster.dat`'s own proven `attack`
    # column (its field 11) in concept, at a different, server-side
    # offset. See `schemas/CLAUDE.md` for the full cross-check against an
    # independent RE pass that reached the same function/formula from the
    # wire-protocol side.
    Column("attack", I32),
    # PROVEN: defense. Uses the SAME `(100-percent)*value/100.0`
    # dispatcher shape `hit_rate`/`attack` use (`0x8140040`, branch on
    # live-instance offset `+0x12c`, divisor `100.0` at VA `0x81f6768`),
    # but this dispatcher's OWN 35 call sites (vs. the 2-3 the other
    # dispatchers have) are the SAME family of element/skill-damage
    # functions `element`/`hit_chance_penalty` already document, and one
    # traced in full (`0x805f150`) shows exactly what it's for: `damage =
    # (attacker_stat_1 + attacker_stat_2) - this_cell's_buffed_value *
    # 1.3` (the `1.3` a literal double at VA `0x81d6388`) -- i.e. it is
    # SUBTRACTED from the attacker's offense to reduce damage, the
    # textbook shape of a defense stat, matching `monster.dat`'s own
    # already-proven `defense` column in concept at a different
    # (server-side) offset.
    Column("defense", I32),
    # REASONED, not fully proven: likely an experience/kill-reward value.
    # NOT `hit_rate` -- an earlier pass here misread this cell's offset
    # (`0x28`) as the one `0x81403e0`'s formula reads; the formula
    # actually reads cell 7 (offset `0x18`, see `hit_rate` above), verified
    # by direct capstone re-disassembly. Corrected 2026-08-19. Tracing
    # what DOES read this cell instead: at least 3 combat-outcome
    # functions (`0x8167a20`, `0x8168b88`, and a third) read it raw and
    # store it through an output pointer whose value gets ADDED into a
    # per-entity accumulator array (`0x39cb55a4 + entity*248 + 0x70`) --
    # every one of them lands on the exact SAME accumulator slot, meaning
    # they are different combat paths feeding one shared "grant reward"
    # mechanism. That shape (a big per-kill value, summed per party
    # member) fits an exp/kill-credit pool; the huge range (0..40 809 717)
    # is consistent with that but was not confirmed against a specific
    # exp display or packet.
    Column("exp_reward", I32),
    # PROVEN: bounds-checked at load time against a runtime config value
    # (read from `28808c64`, presumably a server-side spawn/template cap
    # loaded at startup -- not itself sourced from this file). Real data
    # is near-unique per row (1630 distinct across 5235 rows) and runs in
    # tight consecutive bands within one species' variant rows (1277,
    # 1278, 1279 for the 3 `monster_id=200` rows), which is what a
    # per-variant model/appearance id looks like.
    Column("model_id", I32),
    # STRONGLY REASONED (not fully proven): a live-consumer function
    # (`0x81446a4`) follows a monster instance's `type_id -> monster.scr`
    # join, reads this exact cell (offset `0x30`), multiplies it by 72,
    # and uses that as an index into a THIRD table (base `0x3b97f558`,
    # 72-byte stride) whose offset `0x14` it reads as an int64 reward
    # amount added to the entity's own currency field with an overflow
    # check -- the shape of "look up this monster's loot/reward config
    # and grant it," matching `monster.dat`'s own ALREADY-PROVEN `loot_id`
    # column (see `monster.py`'s `_NAMED`). The third table's own loader
    # was not traced, so the join target itself is not independently
    # confirmed -- only the role (a foreign key feeding a reward payout).
    Column("loot_id", I32),
    # PROVEN: an index into `crt_ai.scr` (`CRT_AI_SCHEMA` in
    # `monster_ai.py`), bounds-checked at load time against the SAME
    # row-count global `crt_ai.scr`'s own loader sets (`0 <= v < crt_ai
    # row count`, `v == 0` also accepted as "no AI"), and both runtime
    # AI-tick consumers read a live monster
    # instance's copy of exactly this cell to pick which `crt_ai.scr` row
    # governs its skill choices. Cross-checked against real data: of
    # 5235 rows only 61 are nonzero, every one lands in `crt_ai.scr`'s
    # populated `1286..2177+` id band, and e.g. the 3 `monster_id=200`
    # rows all carry `ai_id=2174`, which is exactly the row confirmed
    # live under `monster_ai.py`'s weighted-pick proof. See
    # `schemas/CLAUDE.md` for the full derivation.
    Column("ai_id", I32),
    # PROVEN unconsumed: an exhaustive search for any read of this cell's
    # offset (`0x38`) off `0x3b97f544` anywhere in the binary found NONE
    # -- combined with the data being constant `0` across the whole
    # sample, this is a stored-but-dead slot, not merely unobserved-so
    # -far. The "authored, unconsumed" pattern documented throughout
    # `schemas/CLAUDE.md` (e.g. `hard_constant.py`, `mission.py`'s tail).
    Column("field_15", I32),
    # PROVEN discarded: real, widely-varying data (0..924, 769 distinct)
    # that the loader reads but never copies anywhere (same "authored,
    # unconsumed" shape documented for other tables throughout
    # `schemas/CLAUDE.md`, e.g. `hard_constant.py`, `mission.py`'s tail).
    Column("field_16", I32),
    # PROVEN write-only: an exhaustive search for any READ of this cell's
    # spawn-copied destination (`creature+0x6e4`) found only the spawn
    # -init functions themselves WRITING it -- never a read. Near-unique
    # (1491 distinct across 5235 rows), stored to the LAST slot in the
    # record despite being read mid-row (cell 17 of 26) -- the loader's
    # node has room for it out of file order, same shape as `model_id`'s
    # own near-uniqueness -- but nothing in this build ever looks it back
    # up, so its role can't be recovered from a consumer here.
    Column("field_17", I32),
    # REASONED, not fully proven: another monster-grouping flag, sibling
    # to `link_flag` but via a different mechanism. `0x8189480` (walking
    # a live-entity chain via `creature+0x54` as "next") is itself called
    # from `0x8189b18`, which queries a SEPARATE zone-bucket spatial
    # index (`0x3b97f580`, up to 2048 buckets by a map/zone id, not the
    # coordinate bounding box `call_for_help_range` uses) and then
    # notifies up to 11 found entities. This cell gates (`<= 0` vs `> 0`)
    # which "next" field `0x8189480` follows while walking that result
    # set -- `creature+0x54` is the SAME pointer field the
    # `unique_spawn_flag` census also treats as a species-linked chain.
    # Two independently-discovered "notify other monsters of my kind"
    # mechanisms (a tight coordinate box vs. a coarse zone bucket) both
    # touching that same species-chain pointer, gated by their own
    # per-cell flag, is a strong family resemblance to `link_flag` -- but
    # nothing here proves the two flags mean different THINGS rather than
    # just being two independent authoring toggles for two code paths.
    Column("pack_flag", I32),
    # PROVEN the same way as `ai_id`: bounds-checked at load time against
    # `crt_ai.scr`'s own row-count global, `v == 0` also accepted. Only
    # 352 of 5235 rows are nonzero -- a rarely-used second AI reference
    # alongside `ai_id`, role unknown (an alternate/event AI slot is the
    # natural guess given `crt_ai.scr` already has its own per-row
    # trigger mechanism, but nothing here confirms which condition picks
    # this one over `ai_id`).
    Column("secondary_ai_id", I32),
    # REASONED, not fully proven: `0x813e140` walks every LIVE monster
    # instance and, for any whose `monster.scr[type_id]` cell here (offset
    # `0x4c`) is nonzero, checks a 20-slot table at a separate global
    # (`0x3b97f548`) and increments a running count -- the shape of "how
    # many of this (rare) monster type are alive right now," a world
    # -boss/unique-spawn census. Who calls this counter and what limit it
    # enforces was not traced, so the exact role stays a reasoned guess.
    # Boolean-shaped in the data: only 0 or 1 observed, 6/5235 rows
    # nonzero -- consistent with flagging a handful of unique spawns.
    Column("unique_spawn_flag", I32),
    # REASONED, not fully proven: a proc-triggered gold/currency reward,
    # NOT a duration despite a real, separate `*1000` load-time transform
    # (the identical instruction sequence `crt_skill.scr`'s
    # `duration_a_seconds`/`duration_b_seconds` use -- see
    # `monster_skill.py`). Found this cell's TWO actual callers
    # (`0x813a0d3`, `0x813a485`, both inside the same weighted-pick
    # function `monster_ai.py`'s `crt_ai.scr` docs already cover): gated
    # on a live-instance buff/state flag (offset `0x6e8`, checked via
    # `0x81a34ac`, the same "GetStat"-style helper `attack`'s formula
    # uses for ITS percent source), the buffed dispatcher result
    # (`0x81407d4`, the `base * (100+buff%) / 100.0` shape `hit_rate` also
    # uses) is passed STRAIGHT into `0x8136c14` -- the exact same
    # currency-grant function `loot_id` feeds. When that state flag is
    # NOT set, the same call site instead falls through to
    # `GC_ATTACK_CRT2TARGET` (`0x8060dfc`, the monster-attacks-player
    # function documented under `hit_rate`/`attack` above) with
    # `attack_range` as an argument -- i.e. this cell's branch is an
    # ALTERNATIVE outcome to a normal attack-roll, not a stat used every
    # tick. A gold-reward proc (e.g. a "greed"/"lucky" buff effect) is the
    # natural reading of "buffed value -> straight into the money
    # function," gated behind a state flag; the `*1000` transform's role
    # in that story is unclear (possibly serving a different, untraced use
    # of the loader's derived copy). Real data spans 0..22.
    Column("buff_gold_reward", I32),
    # PROVEN *1000 the same way as `field_21_seconds`. Real data spans
    # 0..10800 (i.e. up to 10 800 000 ms = 3 hours) -- a plausible
    # respawn-time range, and this module's own `MONSTER_SCHEMA` above
    # already has a proven-elsewhere `respawn_time` column at a
    # DIFFERENT (client-side) offset, which is why this one is named
    # with the same word rather than left positional -- but nothing in
    # THIS loader's trace ties it to respawning specifically, so treat
    # the name as a strong reasoned guess, not a proven fact the way
    # `ai_id` is. (Cross-checked directly against `monster.dat`'s own
    # `respawn_time` and found no correspondence -- see `schemas/
    # CLAUDE.md`'s monster.py section.)
    Column("respawn_time_seconds", I32),
    # PROVEN: a spawn-scatter radius, not `aggro_range` (an earlier
    # cross-file guess that direct value inspection disproved -- see
    # `schemas/CLAUDE.md`). The function immediately after the loader
    # (`0x813baa8`) reads this cell, computes `rand() % field_23`,
    # subtracts `field_23 / 2` to CENTER the roll, and adds the result to
    # the entity's own base X coordinate (`live_creature+0x48 ->
    # live_creature+0x14`) -- then repeats for Y
    # (`live_creature+0x4c -> +0x18`), then validates the resulting point
    # against the map (a walkability-style call, then a `0x1ff` bounds
    # check). That is exactly "pick a spawn point at a random offset,
    # up to this radius, from my spawn anchor."
    Column("spawn_scatter_range", I32),
    # PROVEN: a call-for-help / aggro-link search radius. `0x81426a0`
    # (gated by `link_flag` below and by a check on `loot_id`'s reward
    # -table row) reads this cell and builds a bounding box
    # `(current_X +/- this, current_Y +/- this)` around the entity, then
    # runs a spatial query over that box (`0x80ff1f0`, results into a
    # 16-entry buffer) and checks each found entity's own `loot_id` reward
    # flags -- the shape of "alert nearby monsters of my own
    # kind/faction when engaged." Also has a PROVEN load-time default:
    # forced to the constant 12 when the file's own value is 0, then
    # checked non-negative. Real data spans 0..150 with 5135/5235 rows
    # nonzero (so the default rarely triggers in practice).
    Column("call_for_help_range", I32),
    # PROVEN: the boolean gate for `call_for_help_range` -- the very
    # first check in `0x81426a0` after the entity/position match is
    # `cmpl $0, this_cell; je <bail>`. Data is boolean-shaped (4611 rows
    # 0, 621 rows 1, 3 outlier rows at 7).
    Column("link_flag", I32),
  ),
)

register_schema("scr", MONSTER_SCR_SCHEMA, patterns=(r"^monster$",))
