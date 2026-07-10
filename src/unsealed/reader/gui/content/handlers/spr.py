"""`.spr` sprite sheets -> an atlas/sprite tree + properties panel."""

from typing import List, Tuple

from ....formats.spr.decoder import SealSprDecoder
from ....vfs import Resource
from ..registry import ContentContext, FormatHandler, register
from ..spr_view import SprView

Quad = Tuple[int, int, int, int]


def _decode(resource: Resource) -> List[Tuple[str, List[Quad]]]:
  return SealSprDecoder(resource.open()).decode()


def _view(entries: List[Tuple[str, List[Quad]]], ctx: ContentContext) -> SprView:
  return SprView(entries, ctx)


register(
  FormatHandler(
    name="Sprite Sheet",
    extensions=(".spr",),
    decode=_decode,
    view=_view,
  )
)
