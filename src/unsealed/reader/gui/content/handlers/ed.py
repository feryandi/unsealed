"""`.ed<n>` item-db shards -> a schema-driven item table.

A shard is an `.edt`-encrypted file (same cipher, claimed by the same
`SealEdtFormat`) whose plaintext is a headerless ItemFile band, so it
decodes in two steps: decrypt, then walk the band into a `DatFile`.

It gets the table view directly rather than the `.edt` `EdtView`: a band
has no self-describing header for `classify` to route on, so there is
nothing to detect — the extension already says what it is.
"""

import re

from ....assets.dat import DatFile
from ....formats.edt.band import band_layout, decode_item_band
from ....formats.edt.format import SealEdtFormat
from ....vfs import Resource
from ..registry import ContentContext, FormatHandler, register
from ..table_sources import DatTableAdapter
from ..table_view import TableView

# `.ed1` … `.ed17`: a numeric band per slice of the item id space.
_BAND_PATTERN = r"\.ed\d+$"
_SUFFIX = re.compile(_BAND_PATTERN, re.IGNORECASE)

# The view re-reads the raw units to re-apply a picked schema, and for a
# band those are the decrypted bytes — not what's on disk. Decrypting is
# a per-byte Python loop over a ~400 KB shard, so `decode` parks the
# plaintext on the asset for `view` instead of paying for it twice.
# Underscored: `tree.py` reflects over public attributes only.
_PLAIN_ATTR = "_plain"


def _decode(resource: Resource) -> DatFile:
  plain = SealEdtFormat().decode(resource).value or b""
  # The band's layout comes from its companion `<stem>.edt` master —
  # resolves for a loose shard and for an `.edp` member alike, since both
  # speak `Resource`.
  dat = decode_item_band(plain, resource.name, band_layout(resource))
  setattr(dat, _PLAIN_ATTR, plain)
  return dat


def _view(dat: DatFile, ctx: ContentContext) -> TableView:
  match = _SUFFIX.search(ctx.resource.name)
  adapter = DatTableAdapter(
    dat,
    getattr(dat, _PLAIN_ATTR, b""),
    ctx.resource.stem,
    header_size=0,  # a band's records start at offset 0: no header, no count
    suffix=match.group(0) if match else "",
  )
  return TableView(adapter)


register(
  FormatHandler(
    name="Item DB Shard",
    extensions=(),
    decode=_decode,
    view=_view,
    patterns=(_BAND_PATTERN,),
  )
)
