"""item_exchange config table (`Seal Online Data` container, columns not yet identified)."""

from .base import Column, DataSchema, I32, register_data_schema

register_data_schema(
  DataSchema(
    name="item_exchange",
    columns=(
      Column("field_0", I32),
      Column("field_1", I32),
      Column("field_2", I32),
      Column("field_3", I32),
      Column("field_4", I32),
      Column("field_5", I32),
      Column("field_6", I32),
      Column("field_7", I32),
      Column("field_8", I32),
      Column("field_9", I32),
      Column("field_10", I32),
      Column("field_11", I32),
      Column("field_12", I32),
      Column("field_13", I32),
      Column("field_14", I32),
      Column("field_15", I32),
      Column("field_16", I32),
      Column("field_17", I32),
      Column("field_18", I32),
      Column("field_19", I32),
      Column("field_20", I32),
      Column("field_21", I32),
    ),
  ),
  patterns=(r"^item_exchange$",),
)
