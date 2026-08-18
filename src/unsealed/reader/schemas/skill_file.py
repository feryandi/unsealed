"""Player skill table (`Seal Online SkillFile v4`, Skill.edt / EDT10003.edt) --
plus the unrelated `skillNN.dat` / `uskill*.dat` band family (see below)."""

from ..formats.bytefields import Column, F32, I32, RecordSchema, Str, register_schema

SKILL_FILE_SCHEMA = RecordSchema(
  name="skill_file",
  columns=(
    Column("id", I32),
    Column("name", Str(36)),
  )
  + tuple(Column(f"field_{i}", I32) for i in range(10, 104)),
)

register_schema(
  "dat",
  SKILL_FILE_SCHEMA,
  type_names=("Seal Online SkillFile",),
  versions=(4,),
)

# --- skillNN.dat / uskill.dat / uskillNN.dat (`SKILL_BAND_SCHEMA`) ---------
#
# Siblings of `skill.py`'s `SKILL_V13_SCHEMA` (`Seal Online Data v13`), not
# of the bespoke v4 header above -- see `skill.py` for the full RE (loader
# address, byte offsets, the proof each field's width is real). This is
# byte-identical to `SKILL_V13_SCHEMA` except one fewer `field_N` at `+303`
# (12 slots instead of 13), giving 971-byte records instead of 975.
#
# No loader was found for these specific filenames (only `skill.dat` itself
# has a traced `CSealTableManager` loader), so this is proven data-only:
# every record of every `skillNN.dat`/`uskillNN.dat`/`uskill.dat` file
# (23 x 363 + 23 x 363 + 4645 rows) decodes with the cursor landing on
# EXACTLY the record boundary and a valid trailing description, with zero
# misalignment. `uskill.dat` additionally has no leading placeholder row
# and non-contiguous `id`s (it is a filtered subset of `skill.dat`'s id
# space -- an "unlockable skills" band, per the `u` prefix).

SKILL_BAND_SCHEMA = RecordSchema(
  name="skill_band",
  columns=(
    Column("id", I32),
    Column("name", Str(255)),
    Column("job_type", I32),
    Column("skill_type", I32),
    Column("field_4", I32),
    Column("key", Str(32)),
    #
    Column("prereq_skill_id", I32),
    Column("prereq_skill_level", I32),
    Column("max_skill_level", I32),
    Column("skill_points", I32),
    Column("min_level", I32),
    Column("required_equip_type", I32),
    Column("field_10", I32),
    Column("ap_cost", I32),
    Column("support_subtype", I32),
    Column("cast_num_target", I32),
    Column("area_of_effect", I32),
    Column("cast_range", I32),
    #
    Column("casting_time", F32),
    Column("duration_seconds", F32),
    Column("cooldown_seconds", F32),
    #
    Column("number_of_hits", I32),
    Column("damage_pct", I32),
    Column("element", I32),
    Column("field_23", I32),
    #
    Column("field_24", I32),
    Column("linked_skill_1", I32),
    Column("buff_1_id", I32),
    Column("buff_1_duration_seconds", I32),
    Column("buff_1_chance", I32),
    Column("linked_skill_2", I32),
    Column("buff_2_id", I32),
    Column("buff_2_duration_seconds", I32),
    Column("buff_2_chance", I32),
    Column("buff_3_id", I32),
    Column("buff_4_id", I32),
    Column("field_35", I32),
    Column("field_36", I32),
    #
    Column("icon_id", I32),
    Column("projectile_speed", I32),
    Column("field_39", I32),
    #
    Column("field_40", I32),
    #
    Column("ultimate_move_pct", F32),
    Column("field_42", F32),
    #
    Column("field_43", I32),
    Column("description", Str(512)),
  ),
)

register_schema(
  "dat",
  SKILL_BAND_SCHEMA,
  patterns=(r"^skill\d+$", r"^uskill$", r"^uskill\d+$"),
  versions=(13,),
)
