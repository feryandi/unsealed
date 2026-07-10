"""`.dat` data files -> a schema-driven table grid.

The file decodes to a `DatFile` (type + version + records); the view
renders those records as a table and lets the user re-apply any
registered `.dat` schema. We keep the raw bytes so a re-applied schema
can re-read the packed records.
"""

from ....assets.dat import DatFile
from ....formats.dat.format import SealDatFormat
from ....vfs import Resource
from ..registry import ContentContext, FormatHandler, register
from ..table_sources import DatTableAdapter
from ..table_view import TableView


def _decode(resource: Resource) -> DatFile:
  return SealDatFormat().decode(resource)


def _view(dat: DatFile, ctx: ContentContext) -> TableView:
  adapter = DatTableAdapter(dat, ctx.resource.read(), ctx.resource.stem)
  return TableView(adapter)


register(
  FormatHandler(
    name="Data Table",
    extensions=(".dat",),
    decode=_decode,
    view=_view,
  )
)
