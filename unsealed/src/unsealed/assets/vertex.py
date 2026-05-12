from typing import List, Optional
from ..core.asset import Asset


class Vertex(Asset):
  """
  Vertex intermediate representation.

  Defines the layout and data for individual vertices, including positions,
  normals, UV coordinates, and bone weights.
  """

  def __init__(
    self,
    position: Optional[List[float]] = None,
    normal: Optional[List[float]] = None,
    texcoord: Optional[List[float]] = None,
  ) -> None:
    self.position: List[float] = position if position is not None else [0.0, 0.0, 0.0]
    self.normal: List[float] = normal if normal is not None else [0.0, 0.0, 0.0]
    self.texcoord: List[float] = texcoord if texcoord is not None else [0.0, 0.0]
    self.joints: List[int] = []
    self.weights: List[int] = []

  def __repr__(self) -> str:
    return (
      f"<Vertex position:{self.position} normal:{self.normal} texcoord:{self.texcoord}>"
    )
