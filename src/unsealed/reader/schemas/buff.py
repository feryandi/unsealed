"""Buff table (`Seal Online Buff v2`) as a declarative schema."""

from ..formats.bytefields import Column, RecordSchema, F32, I32, Str, register_schema

BUFF_SCHEMA = RecordSchema(
  name="buff",
  columns=(
    Column("id", I32),
    Column("name", Str(32)),
    Column("field_36", I32),
    Column("value", I32),  # offset 40: signed effect magnitude
    Column("field_44", I32),
    Column("duration_ms", F32),  # offset 48
    Column("field_52", I32),
    Column("field_56", I32),
    Column("field_60", I32),
    Column("field_64", I32),
  ),
)

register_schema(
  "dat",
  BUFF_SCHEMA,
  type_names=("Seal Online Buff",),
  versions=(2,),
)
