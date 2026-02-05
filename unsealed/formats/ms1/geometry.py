from assets.geometry import Geometry

from formats.ms1.mesh import SealMeshMeshDecoder


class SealMeshGeometryDecoder:
  def __init__(self, file, maybe_non_first_object_has_pad):
    self.file = file
    self.maybe_non_first_object_has_pad = maybe_non_first_object_has_pad

  def decode(self):
    geometry = Geometry()
    count = self.file.read_int()
    for x in range(count):
      if self.maybe_non_first_object_has_pad and x != 0:
        pad = self.file.read(1)
        # Sometimes it has a pad
        if pad == b"\x01":
          self.file.read(12)
      decoder = SealMeshMeshDecoder(self.file)
      mesh = decoder.decode()
      geometry.add_mesh(mesh)
    return geometry
