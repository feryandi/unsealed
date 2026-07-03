"""ItemString table (`Seal Online Data` container, v13).

id + fixed-length name/description strings.
"""

from .base import Column, DataSchema, I32, Str, register_data_schema

register_data_schema(
  DataSchema(
    name="item_string",
    columns=(
      Column("id", I32),
      Column("name", Str(260)),
      Column("description", Str(512)),
    ),
  ),
  patterns=(r"^ItemString$",),
  versions=(13,),
)
