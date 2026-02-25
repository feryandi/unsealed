from typing import Dict, List, Optional
from .vertex import Vertex
from ..core.asset import Asset


class Mesh(Asset):
  """
  Mesh intermediate representation.

  Defines the Mesh class which aggregates geometry, vertices, and
  material assignments for a renderable object.
  """

  def __init__(self, name: str, parent: Optional[str] = None) -> None:
    self.name: str = name
    self.parent: Optional[str] = parent

    self.vertices: List[Vertex] = []
    self.indices: Dict[int, List[int]] = {}
    self.joints: List[List[int]] = []
    self.weights: List[List[float]] = []

    self.tm: Optional[List[List[float]]] = None
    self.material_index: Optional[int] = None

  def add_vertex(self, vertex: Vertex) -> None:
    self.vertices.append(vertex)
    self.joints.append([])
    self.weights.append([])

  def add_index(self, n: int, index: int) -> None:
    if n not in self.indices:
      self.indices[n] = []
    self.indices[n].append(index)

  def add_joint(self, vertex_idx: int, bone_idx: int) -> None:
    self.joints[vertex_idx].append(bone_idx)

  def add_weight(self, vertex_idx: int, weight: float) -> None:
    self.weights[vertex_idx].append(weight)

  def add_transform_matrix(self, transform_matrix: Optional[List[List[float]]]) -> None:
    self.tm = transform_matrix

  def __repr__(self) -> str:
    return f'<Mesh name:"{self.name}">'
