"""Opt_Gem_Cmps_Rst_Grp config table.

A `Seal Online Data` container; columns are not yet identified.
"""

from .base import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="opt_gem_cmps_rst_grp",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
      Column("field_3", I32),
    ),
  ),
  patterns=(r"^Opt_Gem_Cmps_Rst_Grp$",),
)
