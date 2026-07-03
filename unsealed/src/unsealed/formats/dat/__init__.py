"""Seal Online `.dat` data files.

`SealDatDecoder` reads the shared 64-byte header (type + version) and the
int32 element count, then dispatches the records to a `DatBody` from
`registry.py`. Schema-driven types come from the shared `REGISTRY`
(populated by `unsealed.schemas`, imported here for its registration side
effect); the bodies with bespoke decoding (`DataTableBody`,
`QuestFlagBody`) are registered locally.
"""

from ... import schemas  # noqa: F401  — populate REGISTRY (all formats' schemas)
from . import data  # noqa: F401  — DataTableBody (Seal Online Data container)
from . import questflag  # noqa: F401  — QuestFlagBody
