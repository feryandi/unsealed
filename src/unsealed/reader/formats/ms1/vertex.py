from typing import List, Optional

import numpy as np

from ...assets.vertex import Vertex
from ...utils.file import File


class SealMeshVertexDecoder:
  def __init__(self, file: File, transformation_matrix: Optional[List[List[float]]] = None) -> None:
    self.file: File = file
    self.tm: Optional[List[List[float]]] = transformation_matrix

  def decode(self) -> Vertex:
    position = self.__decode_position()
    normal = self.__decode_normal()
    texcoord = self.__decode_texcoord()
    return Vertex(position, normal, texcoord)

  def __decode_position(self) -> List[float]:
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

  def __decode_normal(self) -> List[float]:
    x = self.file.read_float()
    y = self.file.read_float()
    z = self.file.read_float()
    return [x, y, z]

  def __decode_texcoord(self) -> List[float]:
    u = self.file.read_float()
    v = self.file.read_float()
    return [u, v]
