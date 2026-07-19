"""Status coefficient grid (`Seal Online Table1DataFile v1`, status.edt)."""

from ..formats.bytefields import Column, F32, RecordSchema, register_schema

TABLE1_DATA_SCHEMA = RecordSchema(
  name="table1_data",
  columns=(
    Column("stat_index", F32),
    Column("class_index", F32),
    Column("coefficient", F32),
  ),
)

register_schema(
  "dat",
  TABLE1_DATA_SCHEMA,
  type_names=("Seal Online Table1DataFile",),
  versions=(1,),
)
