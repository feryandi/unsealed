"""`.ms1` mesh files -> Model (geometry, materials, meshes, ...)."""

from ....core.asset import Asset
from ....formats.ms1.format import SealMeshFormat
from ....vfs import Resource
from ..registry import FormatHandler, register


def _decode(resource: Resource) -> Asset:
  return SealMeshFormat().decode(resource)


register(
  FormatHandler(
    name="Mesh / Geometry",
    extensions=(".ms1",),
    decode=_decode,
  )
)
