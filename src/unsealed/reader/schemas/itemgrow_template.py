"""Itemgrow_Template config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I64, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="itemgrow_template",
    columns=(
      Column("id", I64),  # the map key; only the low dword is significant
      Column("field_1", I64),  # constant 10
      Column("required_exp", I64),  # inferred; the only field needing int64
      Column("cost", I64),  # money
      Column("success_rate", I64),  # inferred; 100/75/30/10/5/1 per step
      Column("field_5", I64),  # item band; 4 blocks of 6 consecutive ids
      *(
        c
        for i in range(6)
        for c in (
          Column(f"material_{i}_item_id", I64),
          Column(f"material_{i}_count", I64),
        )
      ),
    ),
  ),
  patterns=(r"^Itemgrow_Template$",),
)
