"""`.edp` EDT packages -> an in-app member browser.

An `.edp` bundles the item-db shards as ordinary `.edt`-encrypted files.
The decoder hands them over still encrypted, so double-clicking
`ITEM.ED1` opens it through the very same handler a loose `item.ed1` on
disk would get — nothing here knows about item records.
"""

from ....assets.directory import Directory
from ....formats.edp.format import SealEdpFormat
from ....vfs import Resource
from ..directory_view import DirectoryView
from ..registry import ContentContext, FormatHandler, register


def _decode(resource: Resource) -> Directory:
  return SealEdpFormat().decode(resource)


def _view(directory: Directory, ctx: ContentContext) -> DirectoryView:
  return DirectoryView(directory, ctx)


register(
  FormatHandler(
    name="EDT Package Archive",
    extensions=(".edp",),
    decode=_decode,
    view=_view,
  )
)
