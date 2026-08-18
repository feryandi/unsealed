"""Monster names.

Two on-disk layouts sharing the `id + name` shape, distinguished by
filename (both are generic `Seal Online Data` containers, dispatched by
`DataTableBody` via `schema_for_filename`, not by type): `monster.edt` has
a 144-byte name buffer; `monster_us.edt` (v13, the localized/US client)
widens it to 260 bytes for longer strings.
"""

from ..formats.bytefields import Column, RecordSchema, Str, I32, register_schema

register_schema(
  "dat",
  RecordSchema(
    name="monster_name_us",
    headers=(Column("columns", I32),),
    columns=(
      Column("id", I32),
      Column("name", Str(260)),
    ),
  ),
  patterns=(r"^monster_us$",),
  versions=(13,),
)
