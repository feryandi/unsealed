"""Mon_Grapic (`Seal Online Mon_Grapic File v2`) as a schema.

`count` fixed 36-byte slots; each maps a graphic id (the row index) to a
monster model base name -- a null-terminated string at the slot start,
followed by uninitialised DB-dump garbage. A `Str(36)` column reads the
slot and cuts at the first null, so the garbage tail is dropped exactly
as before. The `<name>.act` derivation is client-side.
"""

from .base import Column, DataSchema, Str, register_type_schema

MON_GRAPIC_SCHEMA = DataSchema(
  name="mon_grapic",
  index_field="id",  # graphic / model id (referenced by monster.dat field 38)
  columns=(Column("model", Str(36)),),
)

register_type_schema(MON_GRAPIC_SCHEMA, "Seal Online Mon_Grapic File", (2,))
