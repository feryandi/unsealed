"""Item-set bonus table (`Seal Online ItemSetOption File v5`, set_opt.edt)."""

from ..formats.bytefields import Column, I32, RecordSchema, register_schema

ITEM_SET_OPTION_SCHEMA = RecordSchema(
  name="item_set_option",
  columns=(
    Column("set_id", I32),
    Column("piece_count", I32),
  )
  + tuple(Column(f"option_value_{i}", I32) for i in range(2, 12))
  + (
    Column("reserved_12", I32),
    Column("reserved_13", I32),
    Column("set_effect_a", I32),
    Column("set_effect_b", I32),
    Column("set_effect_c", I32),
  ),
)

register_schema(
  "dat",
  ITEM_SET_OPTION_SCHEMA,
  type_names=("Seal Online ItemSetOption File",),
  versions=(5,),
)
