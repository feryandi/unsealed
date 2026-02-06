import numpy as np

from ...assets.vertex import Vertex


class SealMeshVertexDecoder:
  def __init__(self, file, transformation_matrix=None):
    self.file = file
    self.tm = transformation_matrix

  def decode(self):
    position = self.__decode_position()
    normal = self.__decode_normal()
    texcoord = self.__decode_texcoord()
    return Vertex(position, normal, texcoord)

  def __decode_position(self):
    x = self.file.read_float()
    y = self.file.read_float()
    z = self.file.read_float()
    position = [x, y, z]

    if self.tm is not None:
      tm = np.array(self.tm)
      tm = np.linalg.inv(tm)
      r = np.dot(np.array(tm).T, np.array([x, y, z, 1]).T)
      position = [r[0], r[1], r[2]]

    return position

  def __decode_normal(self):
    x = self.file.read_float()
    y = self.file.read_float()
    z = self.file.read_float()
    return [x, y, z]

  def __decode_texcoord(self):
    u = self.file.read_float()
    v = self.file.read_float()
    return [u, v]
