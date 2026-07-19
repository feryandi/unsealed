"""Opt_Gem_Cmps config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="opt_gem_cmps",
    columns=(
      Column("id", I32),  # the map key, 0..3
      Column("cost", I32),
      Column("field_2", I32),  # constant 3; no observed reader
    ),
  ),
  patterns=(r"^Opt_Gem_Cmps$",),
)
