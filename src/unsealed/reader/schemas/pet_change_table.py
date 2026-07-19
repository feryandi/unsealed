"""Pet evolution table (`SealOnline PetChangeTable v1`, `p_change.edt`)."""

from ..formats.bytefields import Column, I32, RecordSchema, register_schema

PET_CHANGE_TABLE_SCHEMA = RecordSchema(
  name="pet_change_table",
  headers=(Column("field_count", I32),),  # = 29
  columns=(
    Column("source_pet_id", I32),  # item id of the pet to evolve (128 = Seed)
    Column("result_pet_id", I32),  # item id it evolves into (129 for Seed)
    Column("cost", I32),  # 10-value cost/tier enum (unverified name)
  )
  # 24 material-item-id slots; material_1 is always item 62 (universal catalyst)
  + tuple(Column(f"material_{i}", I32) for i in range(1, 25))
  + (
    # cumulative result-probability %, ascending per recipe group, ends at 100;
    # a result's own chance = this minus the previous row's in the same group
    Column("result_prob_cumulative", I32),
    # recipe group id; (source_pet_id, recipe_group) keys one material set whose
    # rows are its weighted random results
    Column("recipe_group", I32),
  ),
)

register_schema(
  "dat",
  PET_CHANGE_TABLE_SCHEMA,
  type_names=("SealOnline PetChangeTable",),
  versions=(1,),
)
