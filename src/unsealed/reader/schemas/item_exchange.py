"""item_exchange config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="item_exchange",
    columns=(
      Column("id", I32),  # the map key; 0..1064
      Column("field_1", I32),  # constant -1
      Column("item_id", I32),
      Column("exchange_group", I32),
      Column("field_4", I32),  # 0/1
      Column("field_5", I32),  # 0, else 10/11/12
      Column("field_6", I32),  # constant 1
      *(
        c
        for i in range(5)
        for c in (
          Column(f"slot_{i}_item_id", I32),
          Column(f"slot_{i}_count", I32),
          Column(f"slot_{i}_field_2", I32),
        )
      ),
    ),
  ),
  patterns=(r"^item_exchange$",),
)
