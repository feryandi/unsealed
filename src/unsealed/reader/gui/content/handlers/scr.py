"""`.scr` scripts -> a schema-driven table grid (pipe-delimited)."""

from ....assets.scr import Scr
from ....formats.scr.format import SealScrFormat
from ....vfs import Resource
from ..registry import ContentContext, FormatHandler, register
from ..table_sources import CellTableAdapter
from ..table_view import TableView


def _decode(resource: Resource) -> Scr:
  return SealScrFormat().decode(resource)


def _view(scr: Scr, ctx: ContentContext) -> TableView:
  adapter = CellTableAdapter(scr, "scr", ctx.resource.stem)
  return TableView(adapter)


register(
  FormatHandler(
    name="Script Table",
    extensions=(".scr",),
    decode=_decode,
    view=_view,
  )
)
