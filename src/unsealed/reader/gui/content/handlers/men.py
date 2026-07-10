"""`.men` UI files -> an element tree with a properties panel.

The decoder emits a JSON string of the nested element tree; we parse it
back to a dict for the view. stdout is swallowed because older decoder
paths may still print a few raw ints while parsing.
"""

import contextlib
import io
import json
from typing import Any, Dict

from ....formats.men.decoder import SealMenDecoder
from ....vfs import Resource
from ..men_view import MenView
from ..registry import ContentContext, FormatHandler, register


def _decode(resource: Resource) -> Dict[str, Any]:
  buf = io.StringIO()
  with contextlib.redirect_stdout(buf):
    raw = SealMenDecoder(resource.open()).decode()
  return json.loads(raw) if isinstance(raw, str) else (raw or {})


def _view(parsed: Dict[str, Any], ctx: ContentContext) -> MenView:
  return MenView(parsed, ctx)


register(
  FormatHandler(
    name="Menu / UI",
    extensions=(".men",),
    decode=_decode,
    view=_view,
  )
)
