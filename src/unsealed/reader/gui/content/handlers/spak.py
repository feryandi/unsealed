"""`.spak` archives -> an in-app entry browser (opens entries)."""

from ....vfs import Resource
from ..registry import ContentContext, FormatHandler, register
from ..spak_view import SpakView


def _decode(resource: Resource) -> Resource:
  # Nothing to decode up front: the browser mounts the archive itself on
  # a worker thread. Pass the resource through so the view has it.
  return resource


def _view(_asset: Resource, ctx: ContentContext) -> SpakView:
  # A .spak is opened from disk; SpakSource needs the real filesystem
  # path (to zipfile it + glob sibling archives).
  return SpakView(ctx.resource.disk_path, ctx)


register(
  FormatHandler(
    name="SPAK Archive",
    extensions=(".spak",),
    decode=_decode,
    view=_view,
  )
)
