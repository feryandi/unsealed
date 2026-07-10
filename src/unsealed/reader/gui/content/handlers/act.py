"""`.act` actor files -> Model (mesh + named animation actions)."""

from ....formats.act.format import SealActorFormat
from ....vfs import Resource
from ..registry import FormatHandler, register


def _decode(resource: Resource):
  return SealActorFormat().decode(resource)


register(
  FormatHandler(
    name="Actor",
    extensions=(".act",),
    decode=_decode,
  )
)
