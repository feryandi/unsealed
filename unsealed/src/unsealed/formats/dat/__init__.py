"""Seal Online `.dat` data files.

`SealDatDecoder` reads the shared 64-byte header (type + version) and
the int32 element count, then dispatches the records to a `DatBody`
from `registry.py`. Add a new type by registering a `DatBody` and
importing its module HERE so it registers on import, e.g.:

    from . import monster_data  # noqa: F401 (registers the body)
"""

from . import item  # noqa: F401  — registers ItemDataBody
from . import mesh  # noqa: F401  — registers MonGrapicBody
from . import monster  # noqa: F401  — registers MonsterDataBody
from . import quest  # noqa: F401  — registers QuestBody (NPC dialog)
from . import questflag  # noqa: F401  — registers QuestFlagBody
from . import seller  # noqa: F401  — registers SellerDataBody
