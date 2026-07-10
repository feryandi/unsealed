"""`.bn1` bone files -> Skeleton (bone hierarchy + transforms)."""

from ....vfs import Resource
from ..registry import FormatHandler, register


def _decode(resource: Resource):
  # bn1 has no BaseFormat wrapper; drive the raw decoder off the
  # Resource (a disk file or an entry inside a mounted .spak).
  from ....formats.bn1.decoder import SealBoneDecoder

  return SealBoneDecoder(resource.open()).decode()


register(
  FormatHandler(
    name="Skeleton (Bones)",
    extensions=(".bn1",),
    decode=_decode,
  )
)
