"""HardDungeonDecomposition config table (`Seal Online Data` container)."""

from ..formats.bytefields import Column, RecordSchema, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="harddungeondecomposition",
    columns=(
      Column("id", I32),
      Column("item_id", I32),  # the map key: the item being disassembled
      Column("field_2", I32),  # constant 26416, item-id band
      Column("field_3", I32),  # constant 5
      Column("field_4", I32),  # constant 1
      Column("cost", I32),
    )
    # 6..17 are 0 on every row
    + tuple(Column(f"field_{i}", I32) for i in range(6, 18)),
  ),
  patterns=(r"^HardDungeonDecomposition$",),
)
