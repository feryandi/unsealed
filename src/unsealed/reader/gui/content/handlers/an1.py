"""`.an1` animation files -> list of Animation (keyframe tracks)."""

from ....vfs import Resource
from ..registry import FormatHandler, register


def _decode(resource: Resource):
  # Returns a list of Animation nodes; the tree reflects over it. Works
  # for a disk file or an entry inside a mounted .spak.
  from ....formats.an1.decoder import SealAnimationDecoder

  return SealAnimationDecoder(resource.open()).decode()


register(
  FormatHandler(
    name="Animation",
    extensions=(".an1",),
    decode=_decode,
  )
)
