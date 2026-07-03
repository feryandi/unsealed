"""All Seal Online file schemas, in one place.

Importing this package registers every known schema into the shared
`REGISTRY` singleton (defined in `formats/records.py`) -- for `.dat`,
`.scr` and `.tsv` alike. Registration is a pure side effect of import and
is independent of any decoder: a decoder just imports what it needs and
then queries `REGISTRY` (by filename / type name / version, scoped to its
format tag). To add a schema, drop a module under `schemas/` (or
`schemas/dat/`) that registers itself; no decoder changes are required.

    from unsealed.schemas import REGISTRY   # the populated singleton
"""

from ..formats.records import REGISTRY  # noqa: F401  — re-exported entrypoint

from . import dat  # noqa: F401  — .dat schemas (byte tables)
from . import scr  # noqa: F401  — .scr schemas (pipe-delimited)
from . import tsv  # noqa: F401  — .tsv schemas (tab-delimited)
