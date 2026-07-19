"""Stone_OptCost config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="stone_optcost",
    columns=(
      Column("id", I32),  # the map key
      Column("field_1", I32),  # a group; 1 in every sample row
      Column("step", I32),  # 1..N within the group
      Column("item_id", I32),
      Column("field_4", I32),  # rises with step; probably a quantity
      Column("cost", I32),
    ),
  ),
  patterns=(r"^Stone_OptCost$",),
)
