"""iopt_cost config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="iopt_cost",
    columns=(
      Column("index", I32),  # the key: IdentifyItemClass(), 0..4
      Column("ref_money", I32),
      Column("sale", I32),  # percent discount: final = ref_money * (1 - sale/100)
    ),
  ),
  patterns=(r"^iopt_cost$",),
)
