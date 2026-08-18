"""LevelDataFile (`Seal Online LevelDataFile v1`) as a schema."""

from ..formats.bytefields import Column, I32, I64, RecordSchema, register_schema


register_schema(
  "dat",
  RecordSchema(
    name="level_data",
    index_field="level",  # the record index is the level
    columns=(Column("experience_points", I64),),
  ),
  type_names=("Seal Online LevelDataFile",),
  versions=(1,),
  # No filename pattern: `schema_for_filename` returns the FIRST match, and
  # `level.dat`'s generic "Seal Online Data" container needs the `level`
  # schema below, not this one. The GUI picker doesn't need a pattern
  # either -- it lists every schema via REGISTRY.by_format, unfiltered.
)

register_schema(
  "dat",
  RecordSchema(
    name="level",
    columns=(
      Column("level", I32),
      Column("experience_points", I64),
      # PROVEN via live GC_LEVEL_UP_SUCC captures: these two columns are
      # exactly the per-level-up point grant the server applies into two
      # running totals on the player object (player+0x3538, player+0x353c).
      # No client code reads either column locally (only experience_points
      # is used, to fire a level-up request at the server) -- the server
      # computes and sends the totals directly. Which running total is
      # "stat" vs "skill" is still a guess. See schemas/CLAUDE.md > level.py
      # for the full RE + capture trail.
      Column("stat_point_gain", I32),
      Column("sp_gain", I32),
    ),
  ),
  type_names=("Seal Online Data",),
  versions=(1,),
  patterns=(r"^level$",),
)
