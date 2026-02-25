from typing import List
from ..core.asset import Asset


class Vertex(Asset):
  """
  Vertex intermediate representation.

  Defines the layout and data for individual vertices, including positions,
  normals, UV coordinates, and bone weights.
  """

  def __init__(
    self,
    position: List[float] = [0.0, 0.0, 0.0],
    normal: List[float] = [0.0, 0.0, 0.0],
    texcoord: List[float] = [0.0, 0.0],
  ) -> None:
    self.position: List[float] = position
    self.normal: List[float] = normal
    self.texcoord: List[float] = texcoord
    self.joints: List[int] = []
    self.weights: List[int] = []

  def __repr__(self) -> str:
    return (
      f"<Vertex position:{self.position} normal:{self.normal} texcoord:{self.texcoord}>"
    )
