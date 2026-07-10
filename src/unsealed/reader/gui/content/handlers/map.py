"""`.map` terrain files -> a sectioned map overview."""

from pathlib import Path

from ....assets.terrain import Terrain
from ....formats.map.format import SealMapFormat
from ..map_view import MapView
from ..registry import ContentContext, FormatHandler, register


def _decode(path: Path) -> Terrain:
  return SealMapFormat().decode(path)


def _view(terrain: Terrain, ctx: ContentContext) -> MapView:
  return MapView(terrain, ctx)


register(
  FormatHandler(
    name="Map",
    extensions=(".map",),
    decode=_decode,
    view=_view,
  )
)
