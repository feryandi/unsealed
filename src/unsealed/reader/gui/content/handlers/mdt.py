"""`.mdt` model-data archives -> an in-app member browser."""

from ....assets.directory import Directory
from ....formats.mdt.format import SealMdtFormat
from ....vfs import Resource
from ..mdt_view import MdtView
from ..registry import ContentContext, FormatHandler, register


def _decode(resource: Resource) -> Directory:
  return SealMdtFormat().decode(resource)


def _view(directory: Directory, ctx: ContentContext) -> MdtView:
  return MdtView(directory, ctx)


register(
  FormatHandler(
    name="Model Data Archive",
    extensions=(".mdt",),
    decode=_decode,
    view=_view,
  )
)
