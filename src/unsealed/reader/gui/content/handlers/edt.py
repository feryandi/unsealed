"""`.edt` encrypted files -> decrypt, classify, and show the result.

The decoder decrypts the `.edt` and detects what the plaintext actually
is (`.dat`/`.scr`/`.tsv`/xml/binary); `EdtView` then opens that decoded
payload in the same view a loose file of that type would get.
"""

from ....assets.edt import Edt
from ....formats.edt.format import SealEdtFormat
from ....vfs import Resource
from ..edt_view import EdtView
from ..registry import ContentContext, FormatHandler, register


def _decode(resource: Resource) -> Edt:
  return SealEdtFormat().decode(resource)


def _view(edt: Edt, ctx: ContentContext) -> EdtView:
  return EdtView(edt, ctx)


register(
  FormatHandler(
    name="Encrypted Data",
    extensions=(".edt",),
    decode=_decode,
    view=_view,
  )
)
