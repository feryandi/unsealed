"""`.tsv` tables -> a schema-driven table grid (tab-delimited)."""

from ....assets.tsv import Tsv
from ....formats.tsv.format import SealTsvFormat
from ....vfs import Resource
from ..registry import ContentContext, FormatHandler, register
from ..table_sources import CellTableAdapter
from ..table_view import TableView


def _decode(resource: Resource) -> Tsv:
  return SealTsvFormat().decode(resource)


def _view(tsv: Tsv, ctx: ContentContext) -> TableView:
  adapter = CellTableAdapter(tsv, "tsv", ctx.resource.stem)
  return TableView(adapter)


register(
  FormatHandler(
    name="Tab Table",
    extensions=(".tsv",),
    decode=_decode,
    view=_view,
  )
)
