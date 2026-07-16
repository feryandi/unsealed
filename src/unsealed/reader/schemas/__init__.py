"""All Seal Online file schemas, in one place -- one module per schema.

Importing this package registers every known schema into the shared
`REGISTRY` (defined in `formats/records.py`) -- for `.dat`, `.scr` and
`.tsv` alike. Registration is a pure side effect of import and is
independent of any decoder: a decoder just imports this package and then
queries `REGISTRY` (by filename / type name / version, scoped to its
format tag).

    from unsealed.reader.schemas import REGISTRY   # the populated singleton

**To add a schema: drop ONE module in this directory.** It is imported
automatically -- `_load_all()` below walks the package and imports every
module in it, so there is no list to keep in sync here and no decoder to
touch. A module declares its `RecordSchema` and calls `register_schema`
with its own format tag ("dat" / "scr" / "tsv"), which is what files them
apart -- hence the flat directory: the tag lives in the registration, not
in the path. Name the module after the table (`monster.py`, `drop.py`).

The vocabulary a schema module imports lives with the substrate under
`formats/`: `formats/bytefields.py` for `.dat` byte fields (which
re-exports the core, so `.dat` schemas need only that one import), and
`formats/celltable.py` + `formats/records.py` for `.scr`/`.tsv` cells.

A module whose name starts with `_` is skipped, so a private helper shared
by several schemas can live here too without being mistaken for a schema.
Note the auto-import is invisible to PyInstaller's static analysis: both
`.spec`s pass `collect_submodules("unsealed.reader.schemas")` as hidden
imports so frozen builds ship the whole catalogue.
"""

import importlib
import pkgutil

from ..formats.records import REGISTRY  # noqa: F401  — re-exported entrypoint


def _load_all() -> None:
  """Import every schema module here, registering it into `REGISTRY`."""
  for module in pkgutil.iter_modules(__path__):
    if not module.name.startswith("_"):
      importlib.import_module(f"{__name__}.{module.name}")


_load_all()
