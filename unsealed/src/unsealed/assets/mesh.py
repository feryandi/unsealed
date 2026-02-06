from .vertex import Vertex
from ..core.asset import Asset


class Mesh(Asset):
  """
  Mesh intermediate representation.

  Defines the Mesh class which aggregates geometry, vertices, and
  material assignments for a renderable object.
  """

  def __init__(self, name, parent=None):
    self.name = name
    self.parent = parent

    self.vertices = []
    self.indices = {}
    self.old_indices = []
    self.joints = []
    self.weights = []

    self.tm = None
    self.material_index = None

  def add_vertex(self, vertex: Vertex):
    self.vertices.append(vertex)
    self.joints.append([])
    self.weights.append([])

  def add_index(self, n, index):
    if n not in self.indices:
      self.indices[n] = []
    self.indices[n].append(index)
    self.old_indices.append(index)

  def add_joint(self, vertex_idx, bone_idx):
    self.joints[vertex_idx].append(bone_idx)

  def add_weight(self, vertex_idx, weight):
    self.weights[vertex_idx].append(weight)

  def add_transform_matrix(self, transform_matrix):
    self.tm = transform_matrix

  def __repr__(self):
    return f'<Mesh name:"{self.name}">'
