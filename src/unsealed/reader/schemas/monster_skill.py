"""Monster-skill assignment tables: the client's `Seal Online MonsterSkill`
(`Skill_Mon.edt`) and the server's `crt_skill.scr` -- the same eleven-column
shape (verified against real `crt_skill.scr` data, not assumed), so this
module keeps both the way `monster_ai.py` keeps its client/server twins.

`MONSTER_SKILL_SCHEMA` (`.dat`/`.edt`): both known client loaders are pure
copies (structure only, no column meaning -- see `schemas/CLAUDE.md`), so
its names were previously DATA-derived guesses. Two of them are corrected
below from the SERVER's own `crt_skill.scr` loader, reverse-engineered the
same way as `monster_ai.py`'s `crt_ai.scr` (see `schemas/CLAUDE.md` for
the addresses): `CRT_set_skill_script` (`0x8133c10` in `ggg_all2`) atoi's
each of 11 `|`-cells per row, and cells 4 and 5 -- what this schema used to
call `field_4` and `skill_type` -- both go through the IDENTICAL x86
sequence `(v*5 -> v*25 -> v*125) << 3`, i.e. `v * 1000`, before being
stored. That is not a type discriminator; it is a proven unit conversion
(seconds in the file, milliseconds at runtime), so both are renamed
`duration_a_seconds`/`duration_b_seconds` here. The old `skill_type` guess
was reasonable-looking (small integers 1..10-ish) but wrong -- column 5's
real range is 0..450 (i.e. up to 450 000 ms, a 7.5-minute duration), which
a "type" enum would never need.

`CRT_SKILL_SCHEMA` (`.scr`): the loader stores only 8 of the 11 cells
into its 32-byte/8-int32 record (`row * 32`, confirmed both by the stride
arithmetic and by the loader's own `cmpl $0xb, cellIdx` end-of-row check,
`0xb` = 11). Cells 0, 9 and 10 -- `id`, `monster_id`, `field_10` in the
`.dat` schema's naming -- are read (so a short row is still a parse error)
but never copied anywhere: the interpreter simply does not need them at
this file's row count, `id` because it is redundant with the row's own
position (contiguous 0..5754 in the sample, proven the same way
`monster_ai.py`'s `crt_ai.scr` `id` is), `monster_id` and `field_10`
presumably because the row-to-monster association lives entirely in
`monster.scr`'s `skill_N_type`-style references INTO this table (see
`monster.py`) rather than the other direction. Cells 1 and 2 are
range-checked at load time (`0 <= cell <= 13` and `0 <= cell <= 10`
respectively, both bounds confirmed exactly by the real data's min/max),
so they are real small enums even though what they enumerate is not
recoverable from a bounds check alone.
"""

from ..formats.records import Column, I32, RecordSchema, register_schema

MONSTER_SKILL_SCHEMA = RecordSchema(
  name="monster_skill",
  columns=(
    Column("id", I32),
    Column("field_1", I32),
    Column("field_2", I32),
    Column("field_3", I32),
    Column("duration_a_seconds", I32),
    Column("duration_b_seconds", I32),
    Column("skill_id_or_value", I32),
    Column("field_7", I32),
    Column("field_8", I32),
    Column("monster_id", I32),
    Column("field_10", I32),
  ),
)

register_schema(
  "dat",
  MONSTER_SKILL_SCHEMA,
  type_names=("Seal Online MonsterSkill",),
  versions=(1,),
)

CRT_SKILL_SCHEMA = RecordSchema(
  name="crt_skill",
  headers=(Column("row_count", I32),),
  columns=(
    # PROVEN discarded: contiguous 0..count-1 in the file (redundant with
    # the row's own position) and never copied by `CRT_set_skill_script`
    # (its jump-table entry 0 points straight at the "next cell" label).
    Column("id", I32),
    # PROVEN bound: `0 <= v <= 13`, checked at load time before the store
    # (else "ERROR script crt_skill"). Real data tops out at exactly 13.
    Column("field_1", I32),
    # PROVEN bound: `0 <= v <= 10`, same load-time check. Real data tops
    # out at exactly 10.
    Column("field_2", I32),
    # Range 0..50 in the sample; stored as-is, no load-time check seen.
    Column("field_3", I32),
    # PROVEN: the file value is multiplied by 1000 before being stored
    # (`v*5 -> v*25 -> v*125`, then `<<3` = `*8` -- `v*1000` overall). A
    # unit conversion, not a type code -- see the module docstring.
    Column("duration_a_seconds", I32),
    # PROVEN the same way as duration_a_seconds (identical instruction
    # sequence, different destination slot). This is the cell the `.dat`
    # schema used to call `skill_type`; real data ranges 0..450 (i.e. up
    # to 450 000 ms), which rules out a small type enum.
    Column("duration_b_seconds", I32),
    # Range 0..73 698 138 in the sample -- a huge spread that fits the
    # `.dat` schema's "skill id in the common case, a raw magnitude
    # otherwise" reading, but this loader applies no transform or bounds
    # check to it, so that reading is carried over, not reconfirmed here.
    Column("skill_id_or_value", I32),
    # Range 0..940 in the sample; stored as-is.
    Column("field_7", I32),
    # Constant 0 across every sample row -- a real stored slot the data
    # simply never uses.
    Column("field_8", I32),
    # PROVEN discarded, same as `id`: read (and range 0..5536, an
    # item/monster-id-shaped band matching the `.dat` schema's
    # `monster_id` guess) but never copied into the record.
    Column("monster_id", I32),
    # PROVEN discarded, same as `id`/`monster_id`. Range 0..17 in the
    # sample.
    Column("field_10", I32),
  ),
)

register_schema("scr", CRT_SKILL_SCHEMA, patterns=(r"^crt_skill$",))
