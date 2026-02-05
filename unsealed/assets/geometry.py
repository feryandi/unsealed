from typing import List
from assets.mesh import Mesh
from assets.material import Material
from core.asset import Asset


class Geometry(Asset):
  """
  Geometry intermediate representation.

  Contains classes for handling raw geometric data, including index
  buffers and primitive topology definitions.
  """

  def __init__(self):
    self.meshes: List[Mesh] = []
    self.materials: List[Material] = []
    self.mesh_name_to_id = {}

  def add_mesh(self, mesh: Mesh):
    self.meshes.append(mesh)
    self.mesh_name_to_id[mesh.name.lower()] = len(self.meshes) - 1

  def add_material(self, material: Material):
    self.materials.append(material)

  def __repr__(self):
    return f"<Node meshes:{self.meshes}>"
