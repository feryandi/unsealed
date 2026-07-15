"""ItemString table (`Seal Online Data` container, v13).

id + fixed-length name/description strings.
"""

from .base import Column, RecordSchema, I32, Str, register_schema

register_schema(
  "dat",
  RecordSchema(
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
