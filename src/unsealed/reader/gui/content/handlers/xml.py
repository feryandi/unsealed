"""`.xml` data tables -> a table grid with the file's embedded schema.

Seal ships some data tables as XML (the pet `bpet*` family, typically the
plaintext of a `.edt`). The schema lives in the file itself -- the
`<item>` attribute names -- so unlike `.scr`/`.tsv` there is no schema
picker; the grid just shows the columns the decoder extracted.
"""

from ....assets.xml import Xml
from ....formats.xml.format import SealXmlFormat
from ....vfs import Resource
from ..registry import ContentContext, FormatHandler, register
from ..table_sources import XmlTableAdapter
from ..table_view import TableView


def _decode(resource: Resource) -> Xml:
  return SealXmlFormat().decode(resource)


def _view(xml: Xml, ctx: ContentContext) -> TableView:
  adapter = XmlTableAdapter(xml, ctx.resource.stem)
  return TableView(adapter)


register(
  FormatHandler(
    name="XML Table",
    extensions=(".xml",),
    decode=_decode,
    view=_view,
  )
)
