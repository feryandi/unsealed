"""PetFoodTable (`SealOnline PetFoodTable v1`) as a schema.

One extra int32 (`header_extra` = 33, the fields per record), then
`count` records of 33 int32: `pet_id` + 32 food item-id slots. The table
is not zero-terminated -- entries repeat within a row as a weighted
preference table -- so the raw slots are kept as `field_1..field_32`
(any de-dup / weighting is client-side).
"""

from .base import Column, DataSchema, I32, register_type_schema

PET_FOOD_SCHEMA = DataSchema(
  # distinct from the "pet_food" Seal Online Data config table (Pet_Food.dat)
  name="pet_food_table",
  header_extra=1,
  columns=(
    (Column("pet_id", I32),) + tuple(Column(f"field_{i}", I32) for i in range(1, 33))
  ),
)

register_type_schema(PET_FOOD_SCHEMA, "SealOnline PetFoodTable", (1,))
