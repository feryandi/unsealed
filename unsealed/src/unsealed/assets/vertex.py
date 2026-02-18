from typing import List
from ..core.asset import Asset


class Vertex(Asset):
  """
  Vertex intermediate representation.

  Defines the layout and data for individual vertices, including positions,
  normals, UV coordinates, and bone weights.
  """

  def __init__(
    self, position=[0.0, 0.0, 0.0], normal=[0.0, 0.0, 0.0], texcoord=[0.0, 0.0]
  ):
    self.position = [0.0, 0.0, 0.0]
    self.normal = [0.0, 0.0, 0.0]
    self.texcoord = [0.0, 0.0]
    self.joints: List[int] = []
    self.weights: List[int] = []

  def __repr__(self):
    return (
      f"<Vertex position:{self.position} normal:{self.normal} texcoord:{self.texcoord}>"
    )
