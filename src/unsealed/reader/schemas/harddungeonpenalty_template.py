"""HardDungeonpenalty_Template config table (`Seal Online Data` container)."""

from ..formats.bytefields import RecordSchema, register_schema
from .hardfieldpenalty import PENALTY_COLUMNS

register_schema(
  "dat",
  RecordSchema(name="harddungeonpenalty_template", columns=PENALTY_COLUMNS),
  patterns=(r"^HardDungeonpenalty_Template$",),
)
